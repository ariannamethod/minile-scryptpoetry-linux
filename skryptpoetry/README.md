## skryptpoetry ai
Transformer-type translator from human language to the language of skrypts.

### Dependencies

Runtime packages are pinned in `requirements.txt` and `arianna_linux/requirements.txt`. Development and testing tools live in `dev-requirements.txt`.

### Installation

#### Python dependencies

```bash
pip install -r requirements.txt
```

Use the CPU-only wheels to avoid pulling in CUDA libraries:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
export CUDA_VISIBLE_DEVICES=""  # ensure no GPUs are visible
```

#### C compiler (GCC/Clang)

```bash
sudo apt-get update
sudo apt-get install build-essential     # provides gcc
# sudo apt-get install clang             # optional alternative
```

#### Julia

```bash
sudo apt-get install julia
```

#### Java (OpenJDK)

```bash
sudo apt-get install openjdk-17-jdk
```

### Verification

```bash
python --version
gcc --version          # or clang --version
julia --version
java -version
```

### Testing

Run the existing Python test suite:

```bash
pytest
```

Check that each language toolchain builds and runs a trivial program:

```bash
# C
echo 'int main(){return 0;}' > hello.c
gcc hello.c -o hello && ./hello

# Julia
echo 'println("hello")' > hello.jl
julia hello.jl

# Java
cat <<'EOF' > Hello.java
public class Hello { public static void main(String[] args){ System.out.println("hello"); } }
EOF
javac Hello.java && java Hello
```

GPU drivers are not required and should not be installed.

### Docker Image

The `arianna_linux` directory provides a Dockerfile that assembles a CPU-only
environment with build-essential, Julia, and OpenJDK preinstalled alongside the
Python dependencies.

Build the image and start the container:

```bash
docker build -t arianna-linux arianna_linux
docker run --rm -it arianna-linux
```

No GPU libraries are included, keeping the image lightweight and portable.

Skryptpoetry now centers on a lightweight training engine that continuously watches the repository for new knowledge. The trainer hashes eligible files and trains only on those it has not seen before, keeping the process efficient and adaptive to change.

Each request triggers a repository scan to ensure that fresh material is incorporated before any learning happens. This approach allows the model to stay synchronized with evolving datasets without manual intervention or redundant computation.

All interactions are archived through an integrated logging module. It records incoming messages, chosen scripts, and key metrics, providing a chronological record of the model's evolution and the context behind its outputs.

An accompanying metrics library exposes simple measures like entropy, perplexity, and resonance. These statistics offer quick insight into message complexity, prediction surprise, and textual alignment, enabling lightweight diagnostics of model behavior.

The Symphony agent orchestrates training, metrics, and retrieval. Upon receiving a message, it synchronizes the trainer, selects relevant script responses, and logs the resulting interaction, delivering a compact conversational loop.

Datasets stored under the `datasets` and `tongue` directories are automatically parsed whenever they change. By tracking file hashes, the trainer avoids duplicating work while still learning from any new or revised material in those locations.

Supported file types and ignored path segments are configurable through the ``allowed_extensions`` and ``excluded_parts`` parameters of :class:`SkryptTrainer`.

Retrieval of contextual passages is handled internally within Symphony. The agent scans available documents, measures their resonance with the query, and uses the best match to ground its response.

This modular architecture allows future expansion of the model, metrics, and training routines. With the repository constantly monitored, skryptpoetry remains ready to grow alongside new data and ideas.

The repository now includes an incremental training engine that scans designated directories, hashes file contents, and processes only unseen material, keeping the model up to date without redundant work.

Training runs are guarded by a thread lock and can be triggered asynchronously, letting background learning proceed while the system remains responsive to new inputs.

Every interaction and training event is persisted through a SQLite logging layer, creating a complete audit trail of messages, selected scripts, and computed metrics.

A compact metrics library exposes entropy, perplexity, resonance, and token charge, enabling rapid assessment of message complexity, surprise, alignment, and size.

The Symphony agent ties these components together, coordinating training, retrieval, metric calculation, and logging within a simple conversational loop.

Document retrieval employs a Jaccard-based resonance score to compare queries with potential sources and select the most relevant text for grounding responses.

Script selection encourages variety by marking used scripts in the database; when all scripts are exhausted, the system gracefully reuses entries to maintain functionality.

Dataset and script directories are continuously watched for changes, ensuring that new or updated files are incorporated into future training passes.

Concurrency tests confirm that multiple threads invoking training simultaneously still result in a single pass per file, demonstrating correct locking and database usage.

The modular design leaves room for future expansion of models, metrics, and training strategies while keeping the current implementation lightweight and easy to maintain.

## For Developers

The core engine centers on the `Symphony` orchestrator, which coordinates dataset scanning, script retrieval, metric calculation, and logging in a single loop.

Training logic is handled by `SkryptTrainer`, monitoring designated directories and hashing file contents to avoid retraining on material that has already been processed.

Eligible training files are filtered through configurable `allowed_extensions` and `excluded_parts`, allowing precise control over which assets contribute to learning.

A thread-safe scan lock ensures that only one training pass runs at a time, preventing race conditions when multiple requests trigger concurrent scans.

Asynchronous helpers such as `train_async` and `train_on_text_async` offload heavy operations so the interactive session remains responsive while background work continues.

Cached file loading in `symphony.py` stores modification timestamps and contents, minimizing disk reads and stabilizing performance even as datasets grow.

Context retrieval uses a Jaccard-based resonance score to select the document segment most aligned with the current query, grounding responses in relevant data.

`skryptmetrics` exposes entropy, perplexity, resonance, and token-charge utilities, offering quick diagnostics for message complexity, surprise, alignment, and size.

The SQLite-backed logging layer records every user message, chosen script, and metric along with timestamps, providing a complete audit trail for offline inspection.

A dedicated table tracks which scripts have been used to encourage varied responses; once exhausted, the system safely reuses entries to maintain continuity.

Another table stores path and hash pairs for trained files, enabling incremental learning without redundant computation when source material remains unchanged.

The project targets CPU-only environments and pins PyTorch and Transformers versions in `requirements.txt`, ensuring reproducible builds without GPU dependencies.

Python support focuses on CPython 3.10+ and relies solely on the standard library, keeping deployment straightforward on minimal installations.

Optional C, Julia, and Java checks demonstrate multi-language toolchain compatibility, though none are required for core operation of the system.

The self-contained GPT architecture in `model.py` allows developers to load pretrained weights via `from_pretrained` or train new models directly within the repository.

Attention layers enforce causal masking, and optimizer configuration separates decayed from non-decayed parameters for fine-grained regularization control.

High-level text generation APIs are currently absent; responses are drawn from a curated script pool rather than produced by neural decoding routines.

Robust error handling emits warnings for missing files, empty datasets, or database issues and falls back to safe defaults to keep the agent running.

Configuration remains minimal: dataset and script paths are supplied at `Symphony` instantiation, and extension or ignore lists may be overridden in the trainer.

Future extensions can layer richer retrieval strategies, advanced metrics, or full text generation atop the existing modules without refactoring the core.
