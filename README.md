# Academic Agent Suite - Figure Generator

This repository contains tools for generating publication-quality figures for academic papers, following Nature journal style guidelines.

## Overview

The Academic Agent Suite includes a flexible figure generation system that helps researchers create consistent, publication-ready visualizations for their papers. The system provides:

- Line plots, bar plots, and scatter plots with Nature journal styling
- Customizable figure properties (titles, labels, colors, etc.)
- Options for saving in multiple formats (PNG, PDF)
- Base64 encoding for web embedding
- Paper templates with figure integration examples

## Getting Started

### Prerequisites

- Python 3.6+
- NumPy
- Matplotlib

### Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Generate Sample Figures

To see examples of the figure types available, run:

```
python utils/generate_sample_figures.py
```

This will create sample figures in the `static/figures` directory.

For scatter plot examples, run:

```
python utils/generate_scatter_plot.py
```

### Creating Your Own Figures

Import the figure generation functions in your code:

```python
from utils.figure_generator import line_plot, bar_plot, scatter_plot, save_figure
```

#### Line Plot Example

```python
import numpy as np
from utils.figure_generator import line_plot

# Create data
x = np.linspace(0, 2*np.pi, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Generate figure
fig, ax = line_plot(
    x_data=x,
    y_data=[y1, y2],
    title='Trigonometric Functions',
    xlabel='x (radians)',
    ylabel='f(x)',
    labels=['sin(x)', 'cos(x)'],
    filename='my_line_plot',
    formats=['png', 'pdf']
)
```

#### Bar Plot Example

```python
import numpy as np
from utils.figure_generator import bar_plot

# Create data
categories = ['A', 'B', 'C', 'D', 'E']
values = [3.2, 5.7, 8.1, 6.3, 4.8]
errors = [0.5, 0.8, 1.2, 0.7, 0.9]

# Generate figure
fig, ax = bar_plot(
    categories=categories,
    values=values,
    errors=errors,
    title='Sample Measurements',
    xlabel='Category',
    ylabel='Value',
    filename='my_bar_plot',
    formats=['png', 'pdf']
)
```

#### Scatter Plot Example

```python
import numpy as np
from utils.figure_generator import scatter_plot

# Create data
np.random.seed(42)
x = np.random.normal(0, 1, 50)
y = 2 * x + 1 + np.random.normal(0, 0.5, 50)

# Generate figure with trend line
fig, ax = scatter_plot(
    x_data=x, 
    y_data=y, 
    title='Correlation Example',
    xlabel='Independent Variable',
    ylabel='Dependent Variable',
    label='Data Points',
    include_trend=True,
    filename='my_scatter_plot',
    formats=['png', 'pdf']
)
```

### Web Integration

To use figures in web applications, use the `figure_to_base64` function:

```python
from utils.figure_generator import line_plot, figure_to_base64
import numpy as np

# Create data and figure
x = np.linspace(0, 10, 100)
y = np.sin(x)
fig, ax = line_plot(x, [y], title='Sine Wave')

# Convert to base64 for HTML embedding
img_str = figure_to_base64(fig)
```

## Paper Templates

Example paper templates with integrated figures are provided:

- `utils/paper_template_with_figures.md` - A complete academic paper template with figures
- `utils/figures_in_paper_example.md` - A guide for including figures in papers

## Customization

You can customize the Nature style by modifying the `NATURE_STYLE` dictionary in `utils/figure_generator.py`.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Inspired by Nature journal publication guidelines
- Built with Python and Matplotlib 