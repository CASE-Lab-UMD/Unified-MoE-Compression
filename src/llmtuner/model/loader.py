from typing import TYPE_CHECKING, Optional, Tuple

from trl import AutoModelForCausalLMWithValueHead

from transformers import AutoConfig, AutoModel, AutoModelForCausalLM
from transformers import AutoTokenizer
from transformers.integrations import is_deepspeed_zero3_enabled
from .adapter import init_adapter
from .deepseek.configuration_deepseek import DeepseekConfig
from .deepseek.modeling_deepseek import DeepseekModel, DeepseekForCausalLM
from .mixtral.configuration_mixtral import MixtralConfig
from .mixtral.modeling_mixtral import MixtralModel, MixtralForCausalLM
from .qwen.configuration_qwen2_moe import Qwen2MoeConfig
from .qwen.modeling_qwen2_moe import Qwen2MoeModel, Qwen2MoeForCausalLM


from .patcher import patch_config, patch_model, patch_tokenizer, patch_valuehead_model
from .utils import load_valuehead_params, register_autoclass
from ..extras.logging import get_logger
from ..extras.misc import count_parameters, get_current_device, try_download_model_from_ms
from ..hparams import FinetuningArguments

if TYPE_CHECKING:
    from transformers import PreTrainedModel, PreTrainedTokenizer
    from ..hparams import ModelArguments

AutoConfig.register("deepseek", DeepseekConfig)
AutoModel.register(DeepseekConfig, DeepseekModel)
AutoModelForCausalLM.register(DeepseekConfig, DeepseekForCausalLM)

AutoConfig.register("mixtral", MixtralConfig, exist_ok=True)
AutoModel.register(MixtralConfig, MixtralModel, exist_ok=True)
AutoModelForCausalLM.register(MixtralConfig, MixtralForCausalLM, exist_ok=True)

AutoConfig.register("qwen2_moe", Qwen2MoeConfig)
AutoModel.register(Qwen2MoeConfig, Qwen2MoeModel)
AutoModelForCausalLM.register(Qwen2MoeConfig, Qwen2MoeForCausalLM)

logger = get_logger(__name__)


def load_model_and_tokenizer(
        model_args: "ModelArguments",
        is_trainable: Optional[bool] = False,
        add_valuehead: Optional[bool] = False,
        finetuning_args: Optional[FinetuningArguments] = None,
) -> Tuple["PreTrainedModel", "PreTrainedTokenizer"]:
    r"""
    Loads pretrained model and tokenizer.

    Support both training and inference.
    """

    try_download_model_from_ms(model_args)

    config_kwargs = {
        "trust_remote_code": True,
        "cache_dir": model_args.cache_dir,
        "revision": model_args.model_revision,
        "token": model_args.hf_hub_token,
        "attn_implementation": "flash_attention_2",  # 🔍
    }
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            model_args.model_name_or_path,
            use_fast=model_args.use_fast_tokenizer,
            split_special_tokens=model_args.split_special_tokens,
            padding_side="right",
            **config_kwargs,
        )
    except:
        tokenizer = AutoTokenizer.from_pretrained(
            model_args.model_name_or_path,
            use_fast=not model_args.use_fast_tokenizer,  # 🔍
            split_special_tokens=model_args.split_special_tokens,
            padding_side="right",
            **config_kwargs,
        )

    patch_tokenizer(tokenizer)

    config = AutoConfig.from_pretrained(model_args.model_name_or_path, **config_kwargs)
    patch_config(config, tokenizer, model_args, config_kwargs, is_trainable)

    model = None
    if is_trainable and model_args.use_unsloth:
        from unsloth import FastLanguageModel  # type: ignore

        unsloth_kwargs = {
            "model_name": model_args.model_name_or_path,
            "max_seq_length": model_args.model_max_length,
            "dtype": model_args.compute_dtype,
            "load_in_4bit": model_args.quantization_bit == 4,
            "token": model_args.hf_hub_token,
            "device_map": {"": get_current_device()},
            "rope_scaling": getattr(config, "rope_scaling", None),
        }
        try:
            model, _ = FastLanguageModel.from_pretrained(**unsloth_kwargs)
        except NotImplementedError:
            logger.warning("Unsloth does not support model type {}.".format(getattr(config, "model_type", None)))
            model_args.use_unsloth = False

        if model_args.adapter_name_or_path:
            model_args.adapter_name_or_path = None
            logger.warning("Unsloth does not support loading adapters.")

    if model is None:
        if model_args.autoawq:
            from awq import AutoAWQForCausalLM
            trust_remote_code = True

            model = AutoAWQForCausalLM.from_quantized(
                model_args.model_name_or_path,
                trust_remote_code=trust_remote_code,
                safetensors=True
                if model_args.autoawq is True
                else model_args.autoawq.endswith(".safetensors"),
            )

        elif model_args.autogptq:
            from auto_gptq import AutoGPTQForCausalLM

            model = AutoGPTQForCausalLM.from_quantized(
                model_args.model_name_or_path,
                trust_remote_code=False,
                use_safetensors=True
                if model_args.autogptq is True
                else model_args.autogptq.endswith(".safetensors"),
            )

        else:
            model = AutoModelForCausalLM.from_pretrained(
                model_args.model_name_or_path,
                config=config,
                torch_dtype=model_args.compute_dtype,
                low_cpu_mem_usage=(not is_deepspeed_zero3_enabled()),
                **config_kwargs,
            )

    patch_model(model, tokenizer, model_args, is_trainable)
    register_autoclass(config, model, tokenizer)

    if finetuning_args is not None:
        model = init_adapter(model, model_args, finetuning_args, is_trainable)

    if add_valuehead:
        model: "AutoModelForCausalLMWithValueHead" = AutoModelForCausalLMWithValueHead.from_pretrained(model)
        patch_valuehead_model(model)

        if model_args.adapter_name_or_path is not None:
            vhead_path = model_args.adapter_name_or_path[-1]
        else:
            vhead_path = model_args.model_name_or_path

        vhead_params = load_valuehead_params(vhead_path, model_args)
        if vhead_params is not None:
            model.load_state_dict(vhead_params, strict=False)
            logger.info("Loaded valuehead from checkpoint: {}".format(vhead_path))

    if not is_trainable:
        model.requires_grad_(False)
        model = model.to(model_args.compute_dtype) if not getattr(model, "quantization_method", None) else model
        model.eval()
    else:
        model.train()

    trainable_params, all_param = count_parameters(model)
    logger.info(
        "trainable params: {:d} || all params: {:d} || trainable%: {:.4f}".format(
            trainable_params, all_param, 100 * trainable_params / all_param
        )
    )

    if not is_trainable:
        logger.info("This IS expected that the trainable params is 0 if you are using model for inference only.")

    if model_args.print_param_status:
        for name, param in model.named_parameters():
            print(
                "name: {}, dtype: {}, device: {}, trainable: {}".format(
                    name, param.dtype, param.device, param.requires_grad
                )
            )
    for name, module in model.named_modules():
        if hasattr(module, "sparseThreshold"):
            module.sparseThreshold.requires_grad = True

    return model, tokenizer


def load_tokenizer(
        model_args: "ModelArguments",
) -> Tuple["PreTrainedTokenizer"]:
    r"""
    Loads pretrained model and tokenizer.

    Support both training and inference.
    """

    try_download_model_from_ms(model_args)

    config_kwargs = {
        "trust_remote_code": True,
        "cache_dir": model_args.cache_dir,
        "revision": model_args.model_revision,
        "token": model_args.hf_hub_token,
        "attn_implementation": "flash_attention_2",  # 🔍
    }

    tokenizer = AutoTokenizer.from_pretrained(
        model_args.model_name_or_path,
        use_fast=model_args.use_fast_tokenizer,
        split_special_tokens=model_args.split_special_tokens,
        padding_side="right",
        **config_kwargs,
    )

    return tokenizer
