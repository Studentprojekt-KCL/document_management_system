### Environment variables

```dotenv
MINISTRAL_URL=http://<hostname>:11434/api/generate
MINISTRAL_MODEL=model_name
```

### Why Ollama

We chose Ollama for its simplicity within a single Docker container with pull-and-run model management. For our current single user, low-concurrency use case on a 20GB GPU, it is sufficient. However, Ollama has significant limitations that become relevant as the system scales.

---

## What to Improve with Better Hardware

### Larger Models

The RTX 4000 ADA's 20GB VRAM limits us to the 14B parameter model at Q4 quantization. With more VRAM, larger and more capable models become available:

| GPU             | VRAM  | Model options                                         |
|-----------------|-------|-------------------------------------------------------|
| RTX 4000 ADA    | 20GB  | Ministral 3:14B (current)                             |
| RTX 4090        | 24GB  | Mistral Small 22B (quantized Q4)                      |
| A6000 / L40S    | 48GB  | Mistral Small 22B (FP16), Mixtral 8x7B                |
| A100            | 80GB  | Mistral Large, Mixtral 8x22B, Llama 3.1 70B           |
| H100            | 80GB  | Same as A100 but with FP8 support for faster inference |

To switch models in the current Ollama setup, pull the new model and update `.env`:

```bash
sudo docker exec llm-service ollama pull mistral-small:22b
```

```dotenv
MINISTRAL_MODEL=mistral-small:22b
```

No code changes required, the gateway reads the model name from the environment variable.

### Switch Serving Framework

Ollama processes requests sequentially by default and is designed for single user scenarios. Under concurrent load, performance degrades significantly. If the system needs to serve multiple users simultaneously, switching to a production grade serving framework should be considered.

#### vLLM

vLLM is the recommended next step. It uses PagedAttention for efficient GPU memory management and continuous batching to handle concurrent requests without queuing. In benchmarks, vLLM achieves roughly 3-16x higher throughput than Ollama depending on concurrency level and hardware.

vLLM provides an OpenAI-compatible API, so the gateway would need minimal changes — primarily updating the URL and request format.

Best suited for: A100, H100, or multi-GPU setups where concurrent users are expected.

#### TensorRT-LLM

For maximum performance on NVIDIA hardware, TensorRT-LLM compiles models into optimized GPU engines. It achieves the lowest latency and highest throughput of any serving framework, but requires more setup effort, models also need to be converted into TensorRT engines before serving.



TensorRT-LLM supports FP8 quantization on Hopper GPUs (H100), which halves memory usage while maintaining accuracy — enabling larger models on the same hardware.

Best suited for: H100 or Blackwell GPUs in latency-critical production environments where engineering time for setup is available.

### Performance Comparison

Approximate throughput at concurrent load (based on published benchmarks):

| Framework      | Throughput (tokens/sec) | Time-to-first-token | Setup complexity |
|----------------|------------------------|---------------------|------------------|
| Ollama         | ~40 TPS                | ~200-400ms          | Low              |
| vLLM           | ~120-160 req/sec       | ~50-80ms            | Medium           |
| TensorRT-LLM   | ~180-220 req/sec       | ~35-50ms            | High             |

*Numbers are approximate and vary with hardware, model size, and quantization.*

### Multi-GPU

If the machine has multiple GPUs:

- **Ollama**: Does not support tensor parallelism. Can only use one GPU per model.
- **vLLM**: Supports tensor parallelism to split large models across GPUs. Add `--tensor-parallel-size 2` for two GPUs.
- **TensorRT-LLM**: Full multi-GPU and multi-node support for the largest models.

Multi-GPU is required for running 70B+ parameter models that don't fit in a single GPU's VRAM.

### Quantization

Quantization reduces model size and VRAM usage at the cost of some quality:

- **FP16**: Full precision, best quality, highest VRAM usage
- **FP8** (H100/Blackwell only): Half the VRAM of FP16 with minimal quality loss
- **INT8/Q8**: Good quality, ~50% VRAM reduction
- **Q4_K_M**: Significant VRAM savings, noticeable quality reduction for complex tasks

Ollama defaults to Q4 quantization. vLLM and TensorRT-LLM can run FP16 or FP8 natively, which is preferable when VRAM allows it.

### Recommended Upgrade Path

1. **Immediate (no hardware change)**: Increase Ollama parallelism by setting `OLLAMA_NUM_PARALLEL=4` in the Docker environment. Marginal improvement but free.

2. **Mid-term (GPU upgrade to A100/H100)**: Switch to vLLM with a larger model (Mistral Small 22B or Llama 3.1 70B). Significant improvement in both quality and throughput.

3. **Long-term (production scale)**: Deploy TensorRT-LLM on H100 or Blackwell hardware with FP8 quantization. Highest performance, supports multi-GPU for the largest models.