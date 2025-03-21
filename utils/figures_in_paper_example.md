# Using Nature-Style Figures in Your Paper

## Introduction

Figures are a crucial component of academic papers, helping to visualize data and communicate complex concepts effectively. This document demonstrates how to include Nature-style figures generated using our `figure_generator` module in your academic manuscript.

## Line Plots

Line plots are excellent for showing trends over time or relationships between continuous variables. Below is an example of a line plot created with our module:

![Trigonometric Functions](figures/example_line_plot.png "Trigonometric Functions")

*Figure 1: Trigonometric functions sin(x) and cos(x) plotted over the range [0, 10].*

To generate similar plots in your paper, use the following code:

```python
from utils.figure_generator import line_plot
import numpy as np

# Sample data
x = np.linspace(0, 10, 20)
y1 = np.sin(x)
y2 = np.cos(x)

# Create a line plot with two series
fig, ax = line_plot(
    [x, x], [y1, y2], 
    title='Trigonometric Functions',
    xlabel='Time (s)',
    ylabel='Amplitude',
    labels=['sin(x)', 'cos(x)'],
    filename='my_line_plot',  # Will save to static/figures/my_line_plot.png
    formats=['png', 'pdf']    # Save in both PNG and PDF formats
)
```

## Bar Plots

Bar plots are useful for comparing discrete categories:

![Sample Measurements](figures/example_bar_plot.png "Sample Measurements")

*Figure 2: Comparison of values across five sample categories (A-E) with error bars.*

Code to generate bar plots:

```python
from utils.figure_generator import bar_plot

# Sample data
categories = ['A', 'B', 'C', 'D', 'E']
values = [3.5, 2.8, 4.2, 1.9, 3.2]
error_bars = [0.2, 0.3, 0.4, 0.1, 0.3]

# Create a bar plot
fig, ax = bar_plot(
    categories, values,
    title='Sample Measurements',
    xlabel='Sample Category',
    ylabel='Value (units)',
    error_bars=error_bars,
    filename='my_bar_plot'
)
```

## Horizontal Bar Plots

Horizontal bar plots are particularly effective for comparing categories with long labels:

![Journal Impact Factors](figures/journal_impact_factors.png "Journal Impact Factors")

*Figure 3: Comparison of impact factors across major scientific journals.*

Code to generate horizontal bar plots:

```python
from utils.figure_generator import bar_plot

# Sample data
journals = ['Nature', 'Science', 'Cell', 'PNAS', 'PLoS One']
impact_factors = [49.96, 47.73, 41.58, 11.47, 3.24]

# Create a horizontal bar plot
fig, ax = bar_plot(
    journals, impact_factors,
    title='Journal Impact Factors (2022)',
    xlabel='Impact Factor',
    ylabel='Journal',
    horizontal=True,  # Make it horizontal
    filename='journal_comparison'
)
```

## Scatter Plots

Scatter plots are ideal for showing correlations and relationships between variables:

![Correlation Example](figures/correlation_example.png "Correlation Example")

*Figure 4: Correlation between two variables with a fitted trend line.*

![Grouped Data Example](figures/grouped_data_example.png "Grouped Data Example")

*Figure 5: Clustered data points showing distinct groups.*

Code to generate scatter plots:

```python
from utils.figure_generator import scatter_plot
import numpy as np

# Generate sample data
np.random.seed(42)
x = np.random.normal(0, 1, 50)
y = 2 * x + 1 + np.random.normal(0, 0.5, 50)

# Create scatter plot with trend line
fig, ax = scatter_plot(
    x_data=x, 
    y_data=y,
    title='Correlation Example',
    xlabel='Independent Variable',
    ylabel='Dependent Variable',
    label='Data Points',
    include_trend=True,
    filename='my_correlation',
    formats=['png', 'pdf']
)
```

## Integration with Latex Documents

For Latex documents, you may want to save figures in PDF format for better integration:

```python
fig, ax = line_plot(
    x_data, y_data,
    title='My Figure',
    xlabel='X-axis',
    ylabel='Y-axis',
    filename='my_figure',
    formats=['pdf']  # Save only as PDF
)
```

Then in your Latex document:

```latex
\begin{figure}
    \centering
    \includegraphics[width=0.8\textwidth]{figures/my_figure.pdf}
    \caption{Description of the figure.}
    \label{fig:my-figure}
\end{figure}
```

## Conclusion

The Nature-style figure generator provides an easy way to create publication-quality visualizations that adhere to the styling guidelines of top-tier journals. By following the examples in this document, you can efficiently generate and include professional figures in your academic papers. 