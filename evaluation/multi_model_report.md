# Multi-Model Evaluation Report

## Model Comparison

| Model | Accuracy | Precision | Recall | F1 Score | Error Rate | Avg Time (s) |
|:------|:---------|:----------|:-------|:---------|:-----------|:-------------|
| llama3.2 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 2.64 |
| phi3 | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% | 7.27 |
| codellama | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 6.38 |

## Breakdown by Question Type

| Model | Signature Acc | File Acc |
|:------|:--------------|:---------|
| llama3.2 | 0.0% | 0.0% |
| phi3 | 100.0% | 100.0% |
| codellama | 0.0% | 0.0% |

## Detailed Results by Model

### llama3.2

| Question | Judgment | Answer | Ground Truth | Time |
|:---------|:---------|:-------|:-------------|:-----|
| What is the signature of 'PNGLIB_MAJOR'? | INCORRECT | $(PNGCONF) | PNGLIB_MAJOR | 4.97s |
| In which file is 'PNGLIB_MAJOR' defined? | INCORRECT | $(PNGCONF) | scripts/cmake/genout.cmake.in | 0.31s |

### phi3

| Question | Judgment | Answer | Ground Truth | Time |
|:---------|:---------|:-------|:-------------|:-----|
| What is the signature of 'PNGLIB_MAJOR'? | CORRECT | Signature: $(libpng@PNGLIB_MAJOR@@PNGLIB_MINOR@_la_OBJECTS) | PNGLIB_MAJOR | 7.24s |
| In which file is 'PNGLIB_MAJOR' defined? | CORRECT | Makefile.in Signature: $(libpng@PNGLIB_MAJOR@@PNGLIB_MINOR@_ | scripts/cmake/genout.cmake.in | 7.30s |

### codellama

| Question | Judgment | Answer | Ground Truth | Time |
|:---------|:---------|:-------|:-------------|:-----|
| What is the signature of 'PNGLIB_MAJOR'? | INCORRECT | The signature of 'PNGLIB_MAJOR' is '@PNGLIB_MAJOR@'. | PNGLIB_MAJOR | 12.02s |
| In which file is 'PNGLIB_MAJOR' defined? | INCORRECT | `Makefile.in` | scripts/cmake/genout.cmake.in | 0.73s |

