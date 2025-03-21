# Sample Academic Paper with Figures

## Abstract
This template demonstrates how to include publication-quality figures in your academic papers using the figure generator module. The template follows Nature journal style guidelines and showcases different types of visualizations suitable for scientific communication.

## Introduction
Data visualization plays a crucial role in scientific communication, enabling researchers to effectively convey complex information, patterns, and relationships. This paper template demonstrates how to incorporate high-quality figures that adhere to Nature journal style guidelines, ensuring consistency and professional appearance in your academic manuscripts.

## Methodology
For this demonstration, we generate sample data and create visualizations using a custom figure generation module. The figures follow the Nature journal style specifications, including appropriate font sizes, line widths, color schemes, and dimensions. The visualizations are produced using matplotlib with customized parameters to ensure publication-quality output.

## Results

### Time Series Analysis
The analysis of periodic functions reveals characteristic oscillatory behavior as shown in Figure 1. The sine and cosine functions demonstrate regular periodicity with a phase difference of π/2 radians.

![Trigonometric Functions](figures/example_line_plot.png "Trigonometric Functions")

**Figure 1: Trigonometric Functions.** Plot of sine (blue) and cosine (orange) functions over the range [0, 2π], demonstrating the phase relationship between these periodic functions.

### Comparative Analysis
Comparisons between different categories reveal variations in measured values as illustrated in Figure 2. The data shows a general trend of increasing values from Category A to Category E, with the highest measurements observed in Category C.

![Sample Measurements](figures/example_bar_plot.png "Sample Measurements")

**Figure 2: Comparative Measurements.** Bar plot showing measured values across five categories (A-E), with error bars representing standard deviations. Category C exhibits the highest mean value, while Category A shows the lowest.

### Correlation Analysis
Examination of the relationship between variables reveals a strong positive correlation as demonstrated in Figure 3. The scatterplot clearly shows a linear relationship between the independent and dependent variables, with a positive slope indicating that increases in the independent variable are associated with increases in the dependent variable.

![Correlation Example](figures/correlation_example.png "Correlation Example")

**Figure 3: Correlation Analysis.** Scatterplot showing the relationship between independent and dependent variables with a fitted trend line. The data exhibits a strong positive correlation with a linear relationship characterized by the equation y = 2.00x + 1.00.

### Cluster Analysis
Analysis of grouped data points reveals distinct clusters as shown in Figure 4. Two clearly separated groups are identifiable, with Group 1 clustered around the origin and Group 2 centered approximately at coordinates (2, 2).

![Grouped Data Example](figures/grouped_data_example.png "Grouped Data Example")

**Figure 4: Cluster Analysis.** Scatterplot displaying two distinct groups of data points. Group 1 (blue circles) is clustered around the origin, while Group 2 (orange squares) forms a separate cluster centered around (2, 2).

### Impact Analysis
The impact factors of major scientific journals provide insight into their relative influence in the scientific community, as shown in Figure 5. Nature and Science demonstrate the highest impact factors among the analyzed journals.

![Journal Impact Factors](figures/journal_impact_factors.png "Journal Impact Factors")

**Figure 5: Journal Impact Factors.** Horizontal bar chart displaying the impact factors of major scientific journals, with Nature and Science showing the highest values.

## Discussion
The visualizations presented in this paper demonstrate the flexibility and quality of the figure generation approach. By adhering to Nature journal style guidelines, the figures maintain a consistent and professional appearance suitable for high-impact publications. The ability to create various types of plots—including line plots, bar charts, scatter plots with trend lines, and grouped scatter plots—enables effective communication of different types of data and relationships.

## Creating Custom Figures
Researchers can easily generate similar figures using the provided figure generation module. For example, to create a line plot:

```python
from utils.figure_generator import line_plot

# Sample data
x = np.linspace(0, 2*np.pi, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Create and save figure
fig, ax = line_plot(
    x_data=x, 
    y_data=[y1, y2], 
    title='Trigonometric Functions',
    xlabel='x (radians)',
    ylabel='f(x)',
    labels=['sin(x)', 'cos(x)'],
    filename='trig_functions',
    formats=['png', 'pdf']
)
```

To create a scatter plot with a trend line:

```python
from utils.figure_generator import scatter_plot
import numpy as np

# Generate correlated data
np.random.seed(42)
x = np.random.normal(0, 1, 50)
y = 2 * x + 1 + np.random.normal(0, 0.5, 50)

# Create scatter plot with trend line
fig, ax = scatter_plot(
    x, y, 
    title='Correlation Example',
    xlabel='Independent Variable',
    ylabel='Dependent Variable',
    label='Data Points',
    include_trend=True,
    filename='correlation_plot',
    formats=['png', 'pdf']
)
```

## Conclusion
Effective data visualization is essential for scientific communication. By using standardized, publication-quality figures that adhere to journal style guidelines, researchers can enhance the clarity, impact, and professional appearance of their academic papers. The examples presented in this template demonstrate how to create and incorporate various types of figures that meet these high standards.

## References
1. Tufte, E. R. (2001). The Visual Display of Quantitative Information (2nd ed.). Graphics Press.
2. Rougier, N. P., Droettboom, M., & Bourne, P. E. (2014). Ten simple rules for better figures. PLOS Computational Biology, 10(9), e1003833.
3. Wong, B. (2011). Points of view: Color coding. Nature Methods, 8(6), 441. 