import os
import torch
from accelerate import Accelerator

from .utils import check_sparsity_from_state_dict


def save_update_state_dict(save_path, accelerator, update_state_dict):
    accelerator.print("Saving state dicts...")
    if accelerator.is_main_process:
        if not os.path.exists(save_path):
            os.makedirs(save_path)
        torch.save(update_state_dict, os.path.join(save_path, "update_state_dict.pt"))
    accelerator.wait_for_everyone()


def save_sparse_model(prune_model_save_path, model, tokenizer, accelerator: Accelerator, update_state_dict, check_sparsity=True):
    # 🔍 check sparsity
    if check_sparsity and accelerator.is_main_process:
        accelerator.print("*" * 30)
        accelerator.print("Calculating sparsity for pruned params in the state dict...")
        sparsity_ratio = check_sparsity_from_state_dict(update_state_dict)
        accelerator.print(f"sparsity sanity check {sparsity_ratio:.4f}")
        accelerator.print("*" * 30)
    accelerator.wait_for_everyone()

    # 🔍 save
    accelerator.print("Saving models... (may take minutes)")
    if accelerator.is_main_process:
        if not os.path.exists(prune_model_save_path):
            os.makedirs(prune_model_save_path)
    accelerator.wait_for_everyone()

    # get state dict for saving
    save_state_dict = accelerator.get_state_dict(model)

    if save_state_dict is not None:
        accelerator.print(f"State dict stored in CPU on process {accelerator.process_index}")

        # update state dict
        accelerator.print("save_state_dict", list(save_state_dict.keys()))
        accelerator.print("update_state_dict", list(update_state_dict.keys()))

        for name, param in save_state_dict.items():
            if name in update_state_dict:
                accelerator.print(f"Updating {name} (device = {save_state_dict[name].device})")
                save_state_dict[name] = update_state_dict[name]

        # check sparsity
        if check_sparsity:
            accelerator.print("*" * 30)
            accelerator.print("Calculating sparsity for all params in the model after update...")
            sparsity_ratio = check_sparsity_from_state_dict(save_state_dict)
            accelerator.print(f"sparsity sanity check {sparsity_ratio:.4f}")
            accelerator.print("*" * 30)

        # save updated state dict
        unwrapped_model = accelerator.unwrap_model(model)
        unwrapped_model.save_pretrained(
            prune_model_save_path,
            is_main_process=accelerator.is_main_process,
            save_function=accelerator.save,
            state_dict=save_state_dict,
        )
        tokenizer.save_pretrained(prune_model_save_path)

    accelerator.wait_for_everyone()
    accelerator.print(f"Model saved to {prune_model_save_path}")


def save_decomposed_model(prune_model_save_path, model, tokenizer, accelerator: Accelerator, update_state_dict):
    # 🔍 save
    accelerator.print("Saving models... (may take minutes)")
    # accelerator.print(f"update_state_dict: {update_state_dict}")
    if accelerator.is_main_process:
        if not os.path.exists(prune_model_save_path):
            os.makedirs(prune_model_save_path)
    accelerator.wait_for_everyone()

    # get state dict for saving
    save_state_dict = accelerator.get_state_dict(model)

    if save_state_dict is not None:
        accelerator.print(f"State dict stored in CPU on process {accelerator.process_index}")

        # update state dict
        accelerator.print("save_state_dict", list(save_state_dict.keys()))
        accelerator.print("update_state_dict", list(update_state_dict.keys()))

        for name, param in update_state_dict.items():
            accelerator.print(f"Updating {name} (device = {update_state_dict[name].device})")
            save_state_dict[name] = update_state_dict[name]

        # 🔍 initialize a new model and save
        accelerator.print("Initializing the new model...")
        unwrapped_model = accelerator.unwrap_model(model)
        accelerator.print(unwrapped_model.config)
        model_decomposed = type(unwrapped_model)(unwrapped_model.config)
        model_decomposed.load_state_dict(save_state_dict, strict=False)
        model_decomposed.bfloat16()
        accelerator.print("model_decomposed", model_decomposed)
        accelerator.print("Saving...")
        model_decomposed.save_pretrained(prune_model_save_path)
        tokenizer.save_pretrained(prune_model_save_path)

    accelerator.wait_for_everyone()
    accelerator.print(f"Model saved to {prune_model_save_path}")


def save_expert_dropped_model(prune_model_save_path, model, tokenizer, accelerator: Accelerator):
    if accelerator.is_main_process:
        if not os.path.exists(prune_model_save_path):
            os.makedirs(prune_model_save_path)
    accelerator.wait_for_everyone()
    # tokenizer.save_pretrained(prune_model_save_path)
    unwrapped_model = accelerator.unwrap_model(model)
    unwrapped_model.config.save_pretrained(prune_model_save_path)  
    # unwrapped_model.generation_config.save_pretrained(prune_model_save_path)
    # save_decomposed_model(prune_model_save_path, model, tokenizer, accelerator, update_state_dict)
