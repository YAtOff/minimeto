# Reactive Image Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable the agent to detect and view images referenced in the filesystem during its task.

**Architecture:** 
1. Update `read_file` tool schema to advertise image support.
2. Enhance `read_file` implementation to detect image files and return a tagged Base64 string (`__METO_IMAGE__:<path>:<mime>:<data>`).
3. Update pruning logic to skip summarizing these tagged image strings.
4. Update `agent_loop.py` to intercept tagged image strings and inject a multimodal `user` message into the history.

**Tech Stack:** Python, OpenAI Multimodal API (Base64), `mimetypes` library.

---

### Task 1: Update `read_file` Tool Schema

**Files:**
- Modify: `src/meto/agent/tool_schema.py`
- Test: `tests/unit/agent/test_tool_schema_images.py`

- [ ] **Step 1: Write the failing test**

```python
from meto.agent.tool_schema import TOOLS_BY_NAME

def test_read_file_schema_mentions_images():
    schema = TOOLS_BY_NAME["read_file"]
    description = schema["function"]["description"]
    assert "image" in description.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/agent/test_tool_schema_images.py`
Expected: FAIL (assertion error or description doesn't contain "image")

- [ ] **Step 3: Update `read_file` description in `src/meto/agent/tool_schema.py`**

```python
# Change description to:
"Read the contents of a file. Supports text files (returns content) and images (returns visual data for the model to see). Optionally specify a line range for text files."
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add src/meto/agent/tool_schema.py tests/unit/agent/test_tool_schema_images.py
git commit -m "feat: update read_file schema to support images"
```

### Task 2: Implement Image Detection in `read_file`

**Files:**
- Modify: `src/meto/agent/tools/file_tools.py`
- Test: `tests/unit/agent/tools/test_file_image_support.py`

- [ ] **Step 1: Create a small test image**

```bash
# Create a 1x1 black PNG
echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=" | base64 -d > tests/data/pixel.png
```

- [ ] **Step 2: Write failing test for `read_file` with an image**

```python
import base64
from meto.agent.tools.file_tools import read_file
from meto.agent.context import Context

def test_read_file_returns_tagged_image(tmp_path):
    img_path = tmp_path / "test.png"
    data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR..." # minimal png header
    img_path.write_bytes(data)
    
    # Mock context
    ctx = Context(todos=None)
    result = read_file(ctx, str(img_path))
    
    assert result.startswith("__METO_IMAGE__:")
    assert "image/png" in result
    assert base64.b64encode(data).decode() in result
```

- [ ] **Step 3: Update `read_file` in `src/meto/agent/tools/file_tools.py`**

```python
import mimetypes
import base64

# In read_file:
mime, _ = mimetypes.guess_type(file_path)
if mime and mime.startswith("image/"):
    data = file_path.read_bytes()
    b64_data = base64.b64encode(data).decode("utf-8")
    return f"__METO_IMAGE__:{path}:{mime}:{b64_data}"
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add src/meto/agent/tools/file_tools.py tests/unit/agent/tools/test_file_image_support.py
git commit -m "feat: implement image detection and base64 encoding in read_file"
```

### Task 3: Update Pruning Logic to Skip Images

**Files:**
- Modify: `src/meto/agent/autopilot/pruning.py`
- Test: `tests/unit/agent/autopilot/test_pruning_image_skip.py`

- [ ] **Step 1: Write failing test for `summarize_tool_output` with tagged image**

```python
from meto.agent.autopilot.pruning import summarize_tool_output

def test_summarize_skips_tagged_image():
    image_output = "__METO_IMAGE__:path:image/png:base64data..."
    result = summarize_tool_output("read_file", image_output, max_chars=10)
    assert result == image_output
```

- [ ] **Step 2: Update `summarize_tool_output` in `src/meto/agent/autopilot/pruning.py`**

```python
if output.startswith("__METO_IMAGE__:"):
    return output
```

- [ ] **Step 3: Run test to verify it passes**

- [ ] **Step 4: Commit**

```bash
git add src/meto/agent/autopilot/pruning.py tests/unit/agent/autopilot/test_pruning_image_skip.py
git commit -m "fix: skip summarization for tagged image strings"
```

### Task 4: Update Agent Loop for Multimodal Injection

**Files:**
- Modify: `src/meto/agent/agent_loop.py`
- Test: `tests/integration/test_agent_image_loop.py`

- [ ] **Step 1: Write integration test for the image loop**

```python
# Mock get_client().chat.completions.create to return a tool call to read_file
# Verify that the next turn's messages contain a multimodal user message
```

- [ ] **Step 2: Update `run_agent_loop` in `src/meto/agent/agent_loop.py`**

```python
if tool_output.startswith("__METO_IMAGE__:"):
    parts = tool_output.split(":", 3)
    if len(parts) == 4:
        _, img_path, mime, data = parts
        # Update tool result to be human readable
        tool_output = f"[Image loaded: {img_path}]"
        
        # Inject multimodal message
        context.add_message({
            "role": "user",
            "content": [
                {"type": "text", "text": f"Content of {img_path}:"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{data}"}
                }
            ]
        })
```

- [ ] **Step 3: Run integration test to verify it passes**

- [ ] **Step 4: Commit**

```bash
git add src/meto/agent/agent_loop.py tests/integration/test_agent_image_loop.py
git commit -m "feat: inject multimodal message when image is loaded"
```
