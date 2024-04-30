from accelerate import Accelerator
from accelerate.state import AcceleratorState
from copy import deepcopy
from torch.utils.data import DataLoader
from typing import TYPE_CHECKING, List, Optional

from transformers import DataCollatorForSeq2Seq, DataCollatorForLanguageModeling, DataCollatorWithPadding
from .decompose import decompose_moe
from .expert_drop import layerwise_pruning, progressive_pruning, dynamic_skipping, global_pruning, post_experts_drop
from .gate_remap import gate_remap
from .io import save_sparse_model, save_update_state_dict, save_decomposed_model, save_expert_dropped_model
from ..dpo.collator import DPODataCollatorWithPadding
from ..rm.collator import PairwiseDataCollatorWithPadding
from ...data import get_dataset
from ...extras.constants import IGNORE_INDEX
from ...model import load_model_and_tokenizer
from ...train.prune.prune import prune_magnitude, prune_sparsegpt, prune_wanda

if TYPE_CHECKING:
    from transformers import Seq2SeqTrainingArguments, TrainerCallback
    from ...hparams import DataArguments, FinetuningArguments, ModelArguments, PruningArguments

DATA_AWARE_PRUNING_METHODS = ("wanda", "sparsegpt", "gradient-first", "gradient-zeroth", "expert_drop")

EXPERT_DROP_METHODS_FUNC = {
    'layerwise_pruning': layerwise_pruning,
    'global_pruning': global_pruning,
    'progressive_pruning': progressive_pruning,
    'dynamic_skipping': dynamic_skipping,
}


# 🔍 Modified from src.llmtuner.train.pt.workflow.run_pt
def run_prune(
        model_args: "ModelArguments",
        data_args: "DataArguments",
        training_args: "Seq2SeqTrainingArguments",
        finetuning_args: "FinetuningArguments",
        pruning_args: "PruningArguments",  # 🔍 for pruning
        callbacks: Optional[List["TrainerCallback"]] = None,
):
    """Workflow for pruning and decomposing."""
    # 🔍 accelerator
    accelerator = Accelerator()
    accelerator.print(f"{AcceleratorState()}")
    accelerator.print("Pruning Args:", pruning_args)
    accelerator.print("Model Args:", model_args)

    # 🔍 model & tokenizer
    model, tokenizer = load_model_and_tokenizer(model_args, finetuning_args, training_args.do_train)
    # tokenizer = load_tokenizer(model_args)
    if pruning_args.prune_method == "expert_drop" and pruning_args.expert_drop_method == "post_dropping":
        import json
        import os
        with open(os.path.join(pruning_args.prune_model_save_path, "config.json")) as f:
            config = json.load(f)
            layer_experts_idx = config["layer_experts_idx"]            
        post_experts_drop(model, layer_experts_idx, accelerator)
        accelerator.wait_for_everyone()
        accelerator.print(f"model: {model}")
        model.save_pretrained(pruning_args.prune_model_save_path)
        tokenizer.save_pretrained(pruning_args.prune_model_save_path)

        f = open(os.path.join(pruning_args.prune_model_save_path, "config.json"), 'w')
        config_to_save = json.dumps(config, indent=2, sort_keys=True)
        f.write(config_to_save)
        f.close()
        exit()
        
    if pruning_args.prune_method in DATA_AWARE_PRUNING_METHODS:
        # 🔍 dataset & data collator & dataloader
        dataset = get_dataset(tokenizer, model_args, data_args, training_args, stage=pruning_args.prune_data_type)

        if pruning_args.prune_data_type == "pt":
            data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)  # concat all data to seq_length for each batch
        elif pruning_args.prune_data_type == "sft":
            data_collator = DataCollatorForSeq2Seq(
                tokenizer=tokenizer,
                pad_to_multiple_of=8 if tokenizer.padding_side == "right" else None,  # for shift short attention
                label_pad_token_id=IGNORE_INDEX if data_args.ignore_pad_token_for_loss else tokenizer.pad_token_id,
            )
        elif pruning_args.prune_data_type == "rm":
            data_collator = PairwiseDataCollatorWithPadding(tokenizer, pad_to_multiple_of=8)
        elif pruning_args.prune_data_type == "ppo":
            tokenizer.padding_side = "left"  # use left-padding in generation while using right-padding in training
            data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
        else:  # dpo
            data_collator = DPODataCollatorWithPadding(
                tokenizer=tokenizer,
                pad_to_multiple_of=8,
                label_pad_token_id=IGNORE_INDEX if data_args.ignore_pad_token_for_loss else tokenizer.pad_token_id,
            )

        dataloader = DataLoader(dataset, batch_size=1, collate_fn=data_collator, num_workers=8)  # batch size must be 1

        accelerator.print("Total Sample Num:", len(dataset))
        accelerator.print("Total Used Sample Num:", pruning_args.n_calibration_samples)
        accelerator.print("Max sequence Length:", data_args.cutoff_len)
        accelerator.print(f"Example Data (len = {len(dataset[0]['input_ids'])}):", dataset[0])
        if pruning_args.n_calibration_samples > len(dataset):
            raise ValueError("Number of calibration samples is greater than the number of samples in the dataset!")

        # 🔍 Special for expert-drop.
        # We need to wrap the model before "accelerator.prepare" so that the wrapped modules are maintained by DeepSpeed.
        # if pruning_args.prune_method == "expert_drop":
        #     layers = model.model.layers
        #     for l, layer in enumerate(layers):
        #         moe_module = layer.block_sparse_moe
        #
        #         moe_module.r = pruning_args.r
        #         # moe_module.experts_to_drop = None
        #         # moe_module.cache_space = CacheDataset()
        #         # moe_module.cache_logits = False
        #         # moe_module.cache_X = True
        #         # moe_module.cache_Z = True
        #         # moe_module.forward = types.MethodType(prunable_sparse_moe_block.forward, moe_module)
        #         # moe_module.enumerate = types.MethodType(prunable_sparse_moe_block.enumerate, moe_module)
        #         # moe_module.update_dropped_experts = types.MethodType(prunable_sparse_moe_block.update_dropped_experts, moe_module)
        #         # moe_module.prune = types.MethodType(prunable_sparse_moe_block.prune, moe_module)
        #
        #         # layer.block_sparse_moe = PrunableMixtralSparseMoeBlockWrapper(layer.block_sparse_moe, r=pruning_args.r)
        #         # layer.block_sparse_moe.cache_X = True
        #         # layer.block_sparse_moe.cache_Z = True

        # 🔍 Prepare model & dataloader
        print("Preparing model...")
        model, dataloader = accelerator.prepare(model, dataloader)

        # 🔍 Distribute samples to each device for acceleration
        assert (pruning_args.n_calibration_samples % accelerator.num_processes == 0)  # have to be divided evenly
        num_samples_each_device = pruning_args.n_calibration_samples // accelerator.num_processes
        accelerator.print("Number of samples per device:", len(dataloader))
        accelerator.print("Number of used samples per device:", num_samples_each_device)

    else:  # use no additional data for pruning, can be done on 1 GPU
        if AcceleratorState().deepspeed_plugin is not None:
            raise EnvironmentError("Data-independent pruning can only be done without DeepSpeed environment!")
        print("Preparing model...")
        model = accelerator.prepare([model], device_placement=[False])[0]  # 🔍 Prepare model

    #######################################################################################################

    # TODO: Pruning at initialization.
    # Handling n:m sparsity
    prune_n, prune_m = 0, 0
    if pruning_args.sparsity_type != "unstructured" and ":" in pruning_args.sparsity_type:
        assert pruning_args.sparsity_ratio == 0.5, "sparsity ratio must be 0.5 for structured N:M sparsity"
        prune_n, prune_m = map(int, pruning_args.sparsity_type.split(":"))

    if pruning_args.prune_method == "wanda":
        update_state_dict = prune_wanda(pruning_args, model, dataloader, accelerator, num_samples_each_device, prune_n=prune_n, prune_m=prune_m)
        # update_state_dict = prune_wanda_moe(pruning_args, model, dataloader, accelerator, num_samples_each_device, prune_n=prune_n, prune_m=prune_m)
    elif pruning_args.prune_method == "sparsegpt":
        update_state_dict = prune_sparsegpt(pruning_args, model, dataloader, accelerator, num_samples_each_device, prune_n=prune_n, prune_m=prune_m)
    elif pruning_args.prune_method == "gradient-first":
        raise NotImplementedError
    elif pruning_args.prune_method == "gradient-zeroth":
        raise NotImplementedError
    elif pruning_args.prune_method == "magnitude":
        update_state_dict = prune_magnitude(pruning_args, model, accelerator, prune_n=prune_n, prune_m=prune_m)  # Data-independent
    elif pruning_args.prune_method == "decompose_moe":
        update_state_dict = decompose_moe(pruning_args, model, accelerator)  # Data-independent
    elif pruning_args.prune_method == "expert_drop":
        num_local_experts = getattr(accelerator.unwrap_model(model).config, "num_local_experts")
        # remaining_experts = 
        EXPERT_DROP_METHODS_FUNC[pruning_args.expert_drop_method](pruning_args, model, dataloader, accelerator, num_samples_each_device, num_local_experts)

    else:
        raise NotImplementedError
    #######################################################################################################

    # 🔍 Set config for low-rank decomposition.
    accelerator.print(f"model: {model}")

    # 🔍 Save sparse model to disk
    if pruning_args.prune_method == "decompose_moe":
        setattr(accelerator.unwrap_model(model).config, "decomposed", True)
        setattr(accelerator.unwrap_model(model).config, "has_sparse", pruning_args.has_sparse)
        if pruning_args.prune_model_save_path is not None:
            save_decomposed_model(pruning_args.prune_model_save_path, model, tokenizer, accelerator, update_state_dict)
    elif pruning_args.prune_method == "expert_drop":
        # 🔍 only return the idx of remaining experts. 
        if pruning_args.prune_model_save_path is not None:
            save_expert_dropped_model(pruning_args.prune_model_save_path, model, tokenizer, accelerator)
    else:
        if pruning_args.prune_model_save_path is not None:
            save_sparse_model(pruning_args.prune_model_save_path, model, tokenizer, accelerator, update_state_dict, check_sparsity=True)

    accelerator.print("All done!")


def run_prune_remap_gate(
        model_args: "ModelArguments",
        data_args: "DataArguments",
        training_args: "Seq2SeqTrainingArguments",
        finetuning_args: "FinetuningArguments",
        pruning_args: "PruningArguments",  # 🔍 for pruning
        callbacks: Optional[List["TrainerCallback"]] = None,
):
    """Workflow for remapping the gate network."""
    # 🔍 accelerator
    accelerator = Accelerator()
    accelerator.print(f"{AcceleratorState()}")
    accelerator.print("Pruning Args:", pruning_args)
    accelerator.print("Model Args:", model_args)

    if AcceleratorState().deepspeed_plugin is not None:
        raise EnvironmentError("Performing gate-remapping in DeepSpeed environment will result in errors! Use FSDP instead!")

    # 🔍 model & tokenizer
    model, tokenizer = load_model_and_tokenizer(model_args, finetuning_args, training_args.do_train)
    model_pruned_args = deepcopy(model_args)
    model_pruned_args.model_name_or_path = pruning_args.pruned_model_path
    model_pruned, _ = load_model_and_tokenizer(model_pruned_args, finetuning_args, training_args.do_train)

    # tokenizer = load
    # 🔍 dataset & data collator & dataloader
    dataset = get_dataset(tokenizer, model_args, data_args, training_args, stage=pruning_args.prune_data_type)

    if pruning_args.prune_data_type == "pt":
        data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)  # concat all data to seq_length for each batch
    elif pruning_args.prune_data_type == "sft":
        data_collator = DataCollatorForSeq2Seq(
            tokenizer=tokenizer,
            pad_to_multiple_of=8 if tokenizer.padding_side == "right" else None,  # for shift short attention
            label_pad_token_id=IGNORE_INDEX if data_args.ignore_pad_token_for_loss else tokenizer.pad_token_id,
        )
    elif pruning_args.prune_data_type == "rm":
        data_collator = PairwiseDataCollatorWithPadding(tokenizer, pad_to_multiple_of=8)
    elif pruning_args.prune_data_type == "ppo":
        tokenizer.padding_side = "left"  # use left-padding in generation while using right-padding in training
        data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
    else:  # dpo
        data_collator = DPODataCollatorWithPadding(
            tokenizer=tokenizer,
            pad_to_multiple_of=8,
            label_pad_token_id=IGNORE_INDEX if data_args.ignore_pad_token_for_loss else tokenizer.pad_token_id,
        )

    dataloader = DataLoader(dataset, batch_size=1, collate_fn=data_collator, num_workers=8)  # batch size must be 1

    accelerator.print("Total Sample Num:", len(dataset))
    accelerator.print("Total Used Sample Num:", pruning_args.n_calibration_samples)
    accelerator.print("Max sequence Length:", data_args.cutoff_len)
    accelerator.print(f"Example Data (len = {len(dataset[0]['input_ids'])}):", dataset[0])
    if pruning_args.n_calibration_samples > len(dataset):
        raise ValueError("Number of calibration samples is greater than the number of samples in the dataset!")

    # 🔍 Prepare model & dataloader
    print("Preparing model...")
    model, model_pruned, dataloader = accelerator.prepare(model, model_pruned, dataloader)

    # 🔍 Distribute samples to each device for acceleration
    assert (pruning_args.n_calibration_samples % accelerator.num_processes == 0)  # have to be divided evenly
    num_samples_each_device = pruning_args.n_calibration_samples // accelerator.num_processes
    accelerator.print("Number of samples per device:", len(dataloader))
    accelerator.print("Number of used samples per device:", num_samples_each_device)

    #######################################################################################################
    update_state_dict = gate_remap(model, model_pruned, dataloader, accelerator, num_samples_each_device)
    #######################################################################################################

    # Updating the parameters from the state_dict will cause errors in the FSDP environment.
    # So we need to initialize a new model to load it.
    # Here we save the state_dict first to avoid accidents.
    # 🔍 Save state_dict to disk
    if pruning_args.prune_model_save_path is not None:
        save_update_state_dict(pruning_args.prune_model_save_path, accelerator, update_state_dict)

    # 🔍 Reload state_dict and save model
    print("Reloading model and saving...")
    if accelerator.is_main_process:
        model_pruned, _ = load_model_and_tokenizer(model_pruned_args, finetuning_args, training_args.do_train)
        model_pruned.load_state_dict(update_state_dict, strict=False)
        model_pruned.save_pretrained(pruning_args.prune_model_save_path)
        tokenizer.save_pretrained(pruning_args.prune_model_save_path)
        # delete_file_or_dir(os.path.join(pruning_args.prune_model_save_path, "update_state_dict.pt"))
    accelerator.wait_for_everyone()

    accelerator.print("All done!")

