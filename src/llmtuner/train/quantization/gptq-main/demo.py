from transformers import AutoConfig, AutoTokenizer, TextGenerationPipeline
from auto_gptq import AutoGPTQForCausalLM, BaseQuantizeConfig
import logging
import torch
from torch.utils.benchmark import Timer

# logging.basicConfig(
#     format="%(asctime)s %(levelname)s [%(name)s] %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S"
# )

# pretrained_model_dir = "facebook/opt-125m"
# quantized_model_dir = "opt-125m-4bit"

# tokenizer = AutoTokenizer.from_pretrained(pretrained_model_dir, use_fast=True)
# examples = [
#     tokenizer(
#         "auto-gptq is an easy-to-use model quantization library with user-friendly apis, based on GPTQ algorithm."
#     )
# ]

# quantize_config = BaseQuantizeConfig(
#     bits=4,  # quantize model to 4-bit
#     group_size=128,  # it is recommended to set the value to 128
#     desc_act=False,  # set to False can significantly speed up inference but the perplexity may slightly bad
# )

# # load un-quantized model, by default, the model will always be loaded into CPU memory
# config = AutoConfig.from_pretrained(pretrained_model_dir)
# model = AutoGPTQForCausalLM.from_pretrained(pretrained_model_dir, quantize_config)
# layer = model.model.model.decoder.layers[0].cuda()

# x = torch.rand(64, 2048, config.hidden_size).half().cuda()

# with torch.inference_mode():
#     dense_output = layer(x)
#     dense_t = Timer(stmt="layer(x)",
#                     globals={"layer": layer,
#                              "x": x}).blocked_autorange().median * 1e3
#     print(dense_t)
    
    
# quantize model, the examples should be list of dict whose keys can only be "input_ids" and "attention_mask"
# model.quantize(examples)

# # save quantized model
# model.save_quantized(quantized_model_dir)

# # save quantized model using safetensors
# model.save_quantized(quantized_model_dir, use_safetensors=True)

# # push quantized model to Hugging Face Hub.
# # to use use_auth_token=True, Login first via huggingface-cli login.
# # or pass explcit token with: use_auth_token="hf_xxxxxxx"
# # (uncomment the following three lines to enable this feature)
# # repo_id = f"YourUserName/{quantized_model_dir}"
# # commit_message = f"AutoGPTQ model for {pretrained_model_dir}: {quantize_config.bits}bits, gr{quantize_config.group_size}, desc_act={quantize_config.desc_act}"
# # model.push_to_hub(repo_id, commit_message=commit_message, use_auth_token=True)

# # alternatively you can save and push at the same time
# # (uncomment the following three lines to enable this feature)
# # repo_id = f"YourUserName/{quantized_model_dir}"
# # commit_message = f"AutoGPTQ model for {pretrained_model_dir}: {quantize_config.bits}bits, gr{quantize_config.group_size}, desc_act={quantize_config.desc_act}"
# # model.push_to_hub(repo_id, save_dir=quantized_model_dir, use_safetensors=True, commit_message=commit_message, use_auth_token=True)

# # load quantized model to the first GPU
# model = AutoGPTQForCausalLM.from_quantized(quantized_model_dir)

# # download quantized model from Hugging Face Hub and load to the first GPU
# # model = AutoGPTQForCausalLM.from_quantized(repo_id, device="cuda:0", use_safetensors=True, use_triton=False)

# # inference with model.generate
# print(tokenizer.decode(model.generate(**tokenizer("auto_gptq is", return_tensors="pt").to(model.device))[0]))

# # or you can also use pipeline
# pipeline = TextGenerationPipeline(model=model, tokenizer=tokenizer)
# print(pipeline("auto-gptq is")[0]["generated_text"])



import json
import logging
import random
import time
from argparse import ArgumentParser
from itertools import chain
from typing import Dict, List, Optional

import torch
from datasets import Dataset
from tqdm import tqdm
from transformers import AutoTokenizer, GenerationConfig
from transformers.generation.logits_process import LogitsProcessor

from auto_gptq import AutoGPTQForCausalLM, BaseQuantizeConfig


logger = logging.getLogger(__name__)

random.seed(0)


class CustomizedMinNewTokensLogitsProcessor(LogitsProcessor):
    def __init__(
        self,
        min_new_tokens: int = None,
        eos_token_id: int = None,
    ):
        self.eos_token_id = eos_token_id
        self.min_new_tokens = min_new_tokens or 0
        self.current_step = 0

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
        self.current_step += 1

        if self._skip_process():
            return scores

        if any(each is not None for each in [self.eos_token_id]):
            banned_mask = torch.zeros_like(scores).to(scores.device)
            if self.eos_token_id and self.current_step <= self.min_new_tokens:
                banned_mask = self._fill_banned_mask(input_ids, banned_mask, {1: [[self.eos_token_id]]})
            scores = scores.masked_fill(banned_mask.bool(), -float("inf"))

        return scores

    def _skip_process(self):
        if self.current_step > self.min_new_tokens:
            return True
        return False

    @staticmethod
    def _fill_banned_mask(
        input_ids: torch.LongTensor,
        banned_mask: torch.Tensor,
        len2words_ids: Dict[int, List[List[int]]],
    ):
        for token_len, token_ids in len2words_ids.items():
            if token_len == 1:
                banned_mask[..., list(chain(*token_ids))] = 1
            elif input_ids.shape[-1] < token_len - 1:
                continue
            else:
                token_ids = torch.LongTensor(token_ids).to(input_ids.device)
                hit_masks = torch.all(
                    token_ids[..., :-1].unsqueeze(0).repeat(input_ids.shape[0], 1, 1)
                    == input_ids[..., -(token_ids.shape[-1] - 1) :].unsqueeze(1),
                    dim=-1,
                )
                for idx in range(hit_masks.shape[0]):
                    selected_token_ids = torch.masked_select(token_ids[..., -1], hit_masks[idx])
                    if len(selected_token_ids):
                        banned_mask[idx, selected_token_ids] = 1
        return banned_mask


def load_data(data_path, tokenizer, n_samples, max_new_tokens):
    with open(data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    raw_data = random.sample(raw_data, k=min(n_samples, len(raw_data)))

    def dummy_gen():
        return raw_data

    def tokenize(examples):
        instructions = examples["instruction"]
        inputs = examples["input"]
        outputs = examples["output"]

        prompts = []
        texts = []
        input_ids = []
        attention_mask = []
        for istr, inp, opt in zip(instructions, inputs, outputs):
            if inp:
                prompt = f"Instruction:\n{istr}\nInput:\n{inp}\nOutput:\n"
                text = prompt + opt
            else:
                prompt = f"Instruction:\n{istr}\nOutput:\n"
                text = prompt + opt
            if len(tokenizer(prompt)["input_ids"]) >= tokenizer.model_max_length - max_new_tokens:
                continue

            tokenized_data = tokenizer(text)

            input_ids.append(tokenized_data["input_ids"][: tokenizer.model_max_length])
            attention_mask.append(tokenized_data["attention_mask"][: tokenizer.model_max_length])
            prompts.append(prompt)
            texts.append(text)

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "prompt": prompts,
        }

    dataset = Dataset.from_generator(dummy_gen)

    dataset = dataset.map(
        tokenize,
        batched=True,
        batch_size=len(dataset),
        num_proc=1,
        keep_in_memory=True,
        load_from_cache_file=False,
        remove_columns=["instruction", "input"],
    )

    dataset = dataset.to_list()

    for sample in dataset:
        sample["input_ids"] = torch.LongTensor(sample["input_ids"])
        sample["attention_mask"] = torch.LongTensor(sample["attention_mask"])

    return dataset


def load_model_tokenizer(
    model_name_or_path: str,
    tokenizer_name_or_path: Optional[str] = None,
    from_pretrained: bool = False,
    max_memory: Optional[dict] = None,
    model_basename: Optional[str] = None,
    quantize_config: Optional[str] = None,
    trust_remote_code: bool = False,
    use_triton: bool = False,
    use_safetensors: bool = True,
    use_fast_tokenizer: bool = False,
    inject_fused_attention: bool = True,
    inject_fused_mlp: bool = True,
    disable_exllama: bool = False,
):
    tokenizer = AutoTokenizer.from_pretrained(
        pretrained_model_name_or_path=tokenizer_name_or_path or model_name_or_path,
        use_fast=use_fast_tokenizer,
        trust_remote_code=trust_remote_code,
    )
    if not tokenizer.pad_token_id:
        tokenizer.pad_token_id = tokenizer.eos_token_id

    if from_pretrained:
        model = AutoGPTQForCausalLM.from_pretrained(
            pretrained_model_name_or_path=model_name_or_path,
            quantize_config=BaseQuantizeConfig(),
            max_memory=max_memory,
            trust_remote_code=trust_remote_code,
        )
    else:
        model = AutoGPTQForCausalLM.from_quantized(
            model_name_or_path,
            max_memory=max_memory,
            low_cpu_mem_usage=True,
            use_triton=use_triton,
            inject_fused_attention=inject_fused_attention,
            inject_fused_mlp=inject_fused_mlp,
            use_cuda_fp16=True,
            quantize_config=quantize_config,
            model_basename=model_basename,
            use_safetensors=use_safetensors,
            trust_remote_code=trust_remote_code,
            warmup_triton=False,
            disable_exllama=disable_exllama,
        )

    return model, tokenizer


def benchmark_generation_speed(model, tokenizer, examples, generation_config):
    generation_time_list = []
    num_generated_tokens_list = []
    progress_bar = tqdm(examples)
    for example in progress_bar:
        input_ids = example["input_ids"].to(model.device)

        start = time.time()
        outputs_ids = model.generate(
            input_ids=input_ids.unsqueeze(0),
            generation_config=generation_config,
            logits_processor=[
                CustomizedMinNewTokensLogitsProcessor(generation_config.max_new_tokens, tokenizer.eos_token_id)
            ],
        )
        end = time.time()

        generation_time_list.append(end - start)
        num_generated_tokens = 0
        for output_ids in outputs_ids:
            num_generated_tokens += len(
                [token_id for token_id in output_ids[len(input_ids) :] if token_id != tokenizer.pad_token_id]
            )
        num_generated_tokens_list.append(num_generated_tokens)

        progress_bar.set_postfix(
            num_tokens=num_generated_tokens_list[-1],
            time=generation_time_list[-1],
            speed=f"{num_generated_tokens_list[-1] / generation_time_list[-1]:.4f}tokens/s",
        )

    total_tokens = sum(num_generated_tokens_list)
    total_seconds = sum(generation_time_list)
    logger.info(
        f"generated {total_tokens} tokens using {total_seconds} seconds, "
        f"generation speed: {total_tokens / total_seconds}tokens/s"
    )


def main():
    parser = ArgumentParser()
    parser.add_argument("--model_name_or_path", type=str)
    parser.add_argument("--tokenizer_name_or_path", type=str, default=None)
    parser.add_argument("--from_pretrained", action="store_true")
    parser.add_argument("--model_basename", type=str, default=None)
    parser.add_argument("--quantize_config_save_dir", type=str, default=None)
    parser.add_argument("--trust_remote_code", action="store_true")
    parser.add_argument("--use_triton", action="store_true")
    parser.add_argument("--use_safetensors", action="store_true")
    parser.add_argument("--use_fast_tokenizer", action="store_true")
    parser.add_argument("--disable_exllama", action="store_true")
    parser.add_argument("--no_inject_fused_attention", action="store_true")
    parser.add_argument("--no_inject_fused_mlp", action="store_true")
    parser.add_argument("--num_samples", type=int, default=10)
    parser.add_argument("--per_gpu_max_memory", type=int, default=None)
    parser.add_argument("--cpu_max_memory", type=int, default=None)
    parser.add_argument("--max_new_tokens", type=int, default=512)
    parser.add_argument("--do_sample", action="store_true")
    parser.add_argument("--num_beams", type=int, default=1)
    args = parser.parse_args()

    max_memory = {}
    if args.per_gpu_max_memory is not None and args.per_gpu_max_memory > 0:
        if torch.cuda.is_available():
            max_memory.update({i: f"{args.per_gpu_max_memory}GIB" for i in range(torch.cuda.device_count())})
    if args.cpu_max_memory is not None and args.cpu_max_memory > 0 and max_memory:
        max_memory["cpu"] = f"{args.cpu_max_memory}GIB"
    if not max_memory:
        max_memory = None

    logger.info(f"max_memory: {max_memory}")

    quantize_config = None
    if args.quantize_config_save_dir:
        quantize_config = BaseQuantizeConfig.from_pretrained(args.quantize_config_save_dir)

    if args.use_safetensors:
        logger.warning(
            "The command --use_safetensors is deprecated and will be removed in the next release. It is now by default activated."
        )

    logger.info("loading model and tokenizer")
    start = time.time()
    model, tokenizer = load_model_tokenizer(
        model_name_or_path=args.model_name_or_path,
        tokenizer_name_or_path=args.tokenizer_name_or_path,
        from_pretrained=args.from_pretrained,
        max_memory=max_memory,
        model_basename=args.model_basename,
        quantize_config=quantize_config,
        trust_remote_code=args.trust_remote_code,
        use_triton=args.use_triton,
        use_safetensors=True,
        use_fast_tokenizer=args.use_fast_tokenizer,
        inject_fused_attention=not args.no_inject_fused_attention,
        inject_fused_mlp=not args.no_inject_fused_mlp,
        disable_exllama=args.disable_exllama,
    )
    end = time.time()
    logger.info(f"model and tokenizer loading time: {end - start:.4f}s")
    logger.info(f"model quantized: {model.quantized}")
    logger.info(f"quantize config: {model.quantize_config.to_dict()}")
    logger.info(f"model device map: {model.hf_device_map}")

    if args.use_triton:
        logger.info("warmup triton, this may take a while.")
        model.warmup_triton()

    logger.info("loading data")
    examples = load_data(
        "../quantization/dataset/alpaca_data_cleaned.json",
        tokenizer,
        args.num_samples,
        args.max_new_tokens,
    )

    generation_config = GenerationConfig(
        num_beams=args.num_beams,
        num_return_sequences=args.num_beams,
        do_sample=args.do_sample,
        min_new_tokens=args.max_new_tokens,
        max_new_tokens=args.max_new_tokens,
        pad_token_id=tokenizer.pad_token_id,
    )
    logger.info(f"generation config: {generation_config.to_dict()}")

    logger.info("benchmark generation speed")
    benchmark_generation_speed(model, tokenizer, examples, generation_config)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    main()