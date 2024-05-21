import sys

import torch
from accelerate import Accelerator
from tqdm import tqdm
from transformers import MixtralPreTrainedModel

from .utils import find_moe_expert_linears, prepare_calibration_input, print_gpu_memory
from .wrapper import WandaWrapper, SparseGPTWrapper
from ...model.deepseek.modeling_deepseek import DeepseekPreTrainedModel


@torch.no_grad()
def prune_magnitude(args, model, accelerator, prune_n=0, prune_m=0):
    device = accelerator.device
    unwrapped_model = accelerator.unwrap_model(model)  # 🔍 unwrap model first
    use_cache = unwrapped_model.config.use_cache
    unwrapped_model.config.use_cache = False
    layers = unwrapped_model.model.layers

    # 🔍 Get MoE layer ids
    if isinstance(unwrapped_model, MixtralPreTrainedModel):
        num_layers = unwrapped_model.config.num_hidden_layers
        moe_layer_indices = list(range(num_layers))
    elif isinstance(unwrapped_model, DeepseekPreTrainedModel):
        num_layers = unwrapped_model.config.num_hidden_layers
        moe_layer_indices = [layer_idx for layer_idx in range(num_layers) if (unwrapped_model.config.n_routed_experts is not None and layer_idx >= unwrapped_model.config.first_k_dense_replace and layer_idx % unwrapped_model.config.moe_layer_freq == 0)]
    accelerator.print("moe_layer_indices", moe_layer_indices)

    # 🔍 store the pruned parameters in CPU
    update_state_dict = {}

    print('Starting ...')
    for i in tqdm(range(num_layers), desc="Pruning layers..."):
        sys.stderr.flush()
        torch.cuda.empty_cache()
        print_gpu_memory(accelerator)
        layer = layers[i]

        if i in moe_layer_indices:
            # Find modules
            subset = find_moe_expert_linears(layer, exclude_names=args.exclude_prune_module_name)  # 🔍 Find layers to prune

            # Prune
            layer.to(device)  # 🔍
            for name in subset:
                module_state_dict_name = f"model.layers.{i}.{name}"
                print(f"Pruning module {module_state_dict_name}")
                W = subset[name].weight.data
                W_metric = torch.abs(W)
                # print(f"W_metric: {W_metric}")
                if prune_n != 0:
                    W_mask = (torch.zeros_like(W) == 1)
                    for ii in range(W_metric.shape[1]):
                        if ii % prune_m == 0:
                            tmp = W_metric[:, ii:(ii + prune_m)].float()
                            W_mask.scatter_(1, ii + torch.topk(tmp, prune_n, dim=1, largest=False)[1], True)
                else:
                    thresh = torch.sort(W_metric.flatten())[0][int(W.numel() * args.sparsity_ratio)]
                    W_mask = (W_metric <= thresh)

                # 🔍 update the state dict
                # 🔍 the weights would not change if directly updating them using "W[W_mask] = 0"
                update_state_dict[module_state_dict_name + ".weight"] = (W * W_mask).bfloat16().cpu()
            layer.to("cpu")  # 🔍

    print("Pruning done!")
    unwrapped_model.config.use_cache = use_cache
    torch.cuda.empty_cache()

    # 🔍 return the state dict
    return update_state_dict


@torch.no_grad()
def prune_wanda(args, model, dataloader, accelerator: Accelerator, num_samples, prune_n=0, prune_m=0):
    """
    :param num_samples: samples on each device, calculated as "num_samples = n_calibration_samples // num_processes"
    """
    device = accelerator.device
    unwrapped_model = accelerator.unwrap_model(model)  # 🔍 unwrap model first
    use_cache = unwrapped_model.config.use_cache
    unwrapped_model.config.use_cache = False
    layers = unwrapped_model.model.layers

    # 🔍 Get MoE layer ids
    if isinstance(unwrapped_model, MixtralPreTrainedModel):
        num_layers = unwrapped_model.config.num_hidden_layers
        moe_layer_indices = list(range(num_layers))
    elif isinstance(unwrapped_model, DeepseekPreTrainedModel):
        num_layers = unwrapped_model.config.num_hidden_layers
        moe_layer_indices = [layer_idx for layer_idx in range(num_layers) if (unwrapped_model.config.n_routed_experts is not None and layer_idx >= unwrapped_model.config.first_k_dense_replace and layer_idx % unwrapped_model.config.moe_layer_freq == 0)]
    accelerator.print("moe_layer_indices", moe_layer_indices)

    # 🔍 store the pruned parameters in CPU
    update_state_dict = {}

    accelerator.print("Getting features...")
    inputs, outputs, attention_mask, position_ids = prepare_calibration_input(unwrapped_model, dataloader, num_samples)  # 🔍

    accelerator.print('Starting ...')
    for i in tqdm(range(num_layers), desc="Pruning layers...", disable=not accelerator.is_main_process):
        sys.stderr.flush()
        torch.cuda.empty_cache()
        print_gpu_memory(accelerator)
        layer = layers[i]

        if i in moe_layer_indices:
            # Find modules
            subset_experts = find_moe_expert_linears(layer, exclude_names=args.exclude_prune_module_name)  # 🔍 Find layers to prune

            # Wrap layers
            wrapped_layers = {}
            for name in subset_experts:
                wrapped_layers[name] = WandaWrapper(subset_experts[name], layer_name=name, multiply_score=False, p=1)  # 🔍

            # Forward hook for recording row importance
            def add_batch_linear(name):
                def hook(_, input, output):
                    wrapped_layers[name].add_batch_no_score(input[0].data, output.data)

                return hook

            def add_batch_experts(name):
                def hook(_, input, output):
                    wrapped_layers[name].add_batch(input[0].data, output.data, input[1].data if (len(input) >= 2 and input[1] is not None) else None)  # 🔍 input[1] is routing scores.

                return hook

            # Get importance
            handles = []
            for name in wrapped_layers:
                handles.append(subset_experts[name].register_forward_hook(add_batch_experts(name)))
            for j in range(num_samples):
                outputs[j] = layer(inputs[j], attention_mask=attention_mask[j], position_ids=position_ids[j])[0]
            for h in handles:
                h.remove()

            # 🔍 Prune
            for name in subset_experts:  # 🔍semi-structured
                module_state_dict_name = f"model.layers.{i}.{name}"
                accelerator.print(f"Pruning module {module_state_dict_name}")
                W = wrapped_layers[name].weight.data.to(device)  # 👆 use the captured weights
                W_metric = (torch.abs(W) * torch.sqrt(wrapped_layers[name].scaler_row.reshape((1, -1)))).float()
                W_metric = accelerator.reduce(W_metric, reduction="sum")  # 🔍 all reduce across devices
                W_mask = torch.zeros_like(W_metric)  # initialize a mask to be all 0

                if prune_n != 0:
                    # 🔍 semi-structured n:m sparsity
                    for ii in range(W_metric.shape[1]):
                        if ii % prune_m == 0:
                            tmp = W_metric[:, ii:(ii + prune_m)].float()
                            W_mask.scatter_(1, ii + torch.topk(tmp, prune_n, dim=1, largest=False)[1], True)
                else:
                    # 🔍 unstructured
                    sort_res = torch.sort(W_metric, dim=-1, stable=True)

                    if args.use_variant:
                        # wanda variant
                        def return_given_alpha(alpha, sort_res, W_metric, tmp_metric, sum_before):
                            thres_cumsum = sum_before * alpha
                            sort_mask = tmp_metric <= thres_cumsum.reshape((-1, 1))
                            thres = torch.gather(sort_res[0], dim=1, index=sort_mask.sum(dim=1, keepdims=True) - 1)
                            W_mask = (W_metric <= thres)
                            cur_sparsity = (W_mask == True).sum() / W_mask.numel()
                            return W_mask, cur_sparsity

                        tmp_metric = torch.cumsum(sort_res[0], dim=1)
                        sum_before = W_metric.sum(dim=1)

                        alpha = 0.4
                        alpha_hist = [0., 0.8]
                        W_mask, cur_sparsity = return_given_alpha(alpha, sort_res, W_metric, tmp_metric, sum_before)
                        while (torch.abs(cur_sparsity - args.sparsity_ratio) > 0.001) and (alpha_hist[1] - alpha_hist[0] >= 0.001):
                            if cur_sparsity > args.sparsity_ratio:
                                alpha_new = (alpha + alpha_hist[0]) / 2.0
                                alpha_hist[1] = alpha
                            else:
                                alpha_new = (alpha + alpha_hist[1]) / 2.0
                                alpha_hist[0] = alpha

                            alpha = alpha_new
                            W_mask, cur_sparsity = return_given_alpha(alpha, sort_res, W_metric, tmp_metric, sum_before)
                        accelerator.print(f"Alpha found {alpha} sparsity {cur_sparsity:.6f}")
                    else:
                        # unstructured pruning
                        indices = sort_res[1][:, :int(W_metric.shape[1] * args.sparsity_ratio)]
                        W_mask.scatter_(1, indices, True)

                # 🔍 update the state dict
                # 🔍 the weights would not change if directly updating them using "W.data[W_mask] = 0"
                update_state_dict[module_state_dict_name + ".weight"] = (W * (torch.ones_like(W_mask) - W_mask)).bfloat16().cpu()

        else:
            for j in range(num_samples):
                outputs[j] = layer(inputs[j], attention_mask=attention_mask[j], position_ids=position_ids[j])[0]

        # Update inputs & outputs
        inputs, outputs = outputs, inputs

    accelerator.print("Pruning done!")
    unwrapped_model.config.use_cache = use_cache
    torch.cuda.empty_cache()

    # 🔍 return the state dict
    return update_state_dict


@torch.no_grad()
def prune_sparsegpt(args, model, dataloader, accelerator: Accelerator, num_samples, prune_n=0, prune_m=0, blocksize=128, percdamp=0.01):
    """
        SparseGPT code available at: https://github.com/IST-DASLab/sparsegpt/tree/f5c25005a61f96a0933ca2f95705a963585aafaa
        :param num_samples: samples on each device, calculated as "num_samples = n_calibration_samples // num_processes"
    """
    device = accelerator.device
    unwrapped_model = accelerator.unwrap_model(model)  # 🔍 unwrap model first
    use_cache = unwrapped_model.config.use_cache
    unwrapped_model.config.use_cache = False
    layers = unwrapped_model.model.layers

    # 🔍 Get MoE layer ids
    if isinstance(unwrapped_model, MixtralPreTrainedModel):
        num_layers = unwrapped_model.config.num_hidden_layers
        moe_layer_indices = list(range(num_layers))
    elif isinstance(unwrapped_model, DeepseekPreTrainedModel):
        num_layers = unwrapped_model.config.num_hidden_layers
        moe_layer_indices = [layer_idx for layer_idx in range(num_layers) if (unwrapped_model.config.n_routed_experts is not None and layer_idx >= unwrapped_model.config.first_k_dense_replace and layer_idx % unwrapped_model.config.moe_layer_freq == 0)]
    accelerator.print("moe_layer_indices", moe_layer_indices)

    # 🔍 store the pruned parameters in CPU
    update_state_dict = {}

    accelerator.print("Getting features...")
    inputs, outputs, attention_mask, position_ids = prepare_calibration_input(unwrapped_model, dataloader, num_samples)  # 🔍

    accelerator.print('Starting ...')
    for i in tqdm(range(len(layers)), desc="Pruning layers...", disable=not accelerator.is_main_process):
        sys.stderr.flush()
        torch.cuda.empty_cache()
        print_gpu_memory(accelerator)
        layer = layers[i]

        if i in moe_layer_indices:
            # Find modules
            subset = find_moe_expert_linears(layer, exclude_names=args.exclude_prune_module_name)  # 🔍 Find layers to prune

            # Wrap layers
            wrapped_layers = {}
            for name in subset:
                wrapped_layers[name] = SparseGPTWrapper(subset[name])

            def add_batch(name):
                def hook(_, input, output):
                    wrapped_layers[name].add_batch(input[0].data, output.data)

                return hook

            # Get importance
            handles = []
            for name in wrapped_layers:
                handles.append(subset[name].register_forward_hook(add_batch(name)))
            for j in range(num_samples):
                outputs[j] = layer(inputs[j], attention_mask=attention_mask[j], position_ids=position_ids[j])[0]
            for h in handles:
                h.remove()

            # Prune
            for name in wrapped_layers:
                module_state_dict_name = f"model.layers.{i}.{name}"
                accelerator.print(f"Pruning module {module_state_dict_name}")

                W = wrapped_layers[name].weight.data.to(device).float()  # 👆 use the captured weights
                H = wrapped_layers[name].H
                H = accelerator.reduce(H, reduction="mean")  # 🔍 all reduce across devices

                dead = (torch.diag(H) == 0)
                H[dead, dead] = 1
                W[:, dead] = 0

                Losses = torch.zeros(wrapped_layers[name].rows, device=wrapped_layers[name].device)

                damp = percdamp * torch.mean(torch.diag(H))
                diag = torch.arange(wrapped_layers[name].columns, device=wrapped_layers[name].device)
                H[diag, diag] += damp
                H = torch.linalg.cholesky(H)
                H = torch.cholesky_inverse(H)
                H = torch.linalg.cholesky(H, upper=True)
                Hinv = H

                mask = None

                # formally begin
                for i1 in range(0, wrapped_layers[name].columns, blocksize):
                    i2 = min(i1 + blocksize, wrapped_layers[name].columns)
                    count = i2 - i1

                    W1 = W[:, i1:i2].clone()
                    Q1 = torch.zeros_like(W1)
                    Err1 = torch.zeros_like(W1)
                    Losses1 = torch.zeros_like(W1)
                    Hinv1 = Hinv[i1:i2, i1:i2]

                    if prune_n == 0:
                        if mask is not None:
                            mask1 = mask[:, i1:i2]
                        else:
                            tmp = W1 ** 2 / (torch.diag(Hinv1).reshape((1, -1))) ** 2
                            thresh = torch.sort(tmp.flatten())[0][int(tmp.numel() * args.sparsity_ratio)]
                            mask1 = (tmp <= thresh)
                    else:
                        mask1 = (torch.zeros_like(W1) == 1)

                    for j in range(count):
                        w = W1[:, j]
                        d = Hinv1[j, j]

                        if prune_n != 0 and j % prune_m == 0:
                            tmp = W1[:, j:(j + prune_m)] ** 2 / (torch.diag(Hinv1)[j:(j + prune_m)].reshape((1, -1))) ** 2
                            mask1.scatter_(1, j + torch.topk(tmp, prune_n, dim=1, largest=False)[1], True)

                        q = w.clone()
                        q[mask1[:, j]] = 0

                        Q1[:, j] = q
                        Losses1[:, j] = (w - q) ** 2 / d ** 2

                        err1 = (w - q) / d
                        W1[:, j:] -= err1.unsqueeze(1).matmul(Hinv1[j, j:].unsqueeze(0))
                        Err1[:, j] = err1

                    W[:, i1:i2] = Q1
                    Losses += torch.sum(Losses1, 1) / 2
                    W[:, i2:] -= Err1.matmul(Hinv[i1:i2, i2:])

                # 🔍 update the state dict
                # 🔍 the weights would not change if directly applying them
                update_state_dict[module_state_dict_name + ".weight"] = W.bfloat16().cpu()

        else:
            for j in range(num_samples):
                outputs[j] = layer(inputs[j], attention_mask=attention_mask[j], position_ids=position_ids[j])[0]

        # Update inputs & outputs
        inputs, outputs = outputs, inputs

    accelerator.print("Pruning done!")
    unwrapped_model.config.use_cache = use_cache
    torch.cuda.empty_cache()

    # 🔍 return the state dict
    return update_state_dict
