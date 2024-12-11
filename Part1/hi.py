from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak

# Data for the table (Sample data repeated to increase the table size)
data = [
    ["Method", "Description", "Application"],
    ["One-Sided ANOVA", "Tests if the means of several groups are significantly different from each other, focusing on one side of the distribution.", "Testing for differences in group means when focusing on one side of the distribution."],
    ["Two-Sided ANOVA", "Tests if the means of several groups are significantly different from each other, considering both sides of the distribution.", "Testing for differences in group means considering both sides of the distribution."],
    ["Chi-Square Test", "Tests if there is a significant association between categorical variables.", "Assessing associations between categorical variables."],
    ["Poisson Distribution", "Models the number of events occurring within a fixed interval of time or space.", "Modeling the number of events occurring within a fixed time or space."],
    ["Z-Test", "Tests if the means of two populations are different, assuming large sample sizes.", "Comparing means of two populations with large sample sizes."],
    ["T-Test", "Tests if the means of two populations are different, assuming smaller sample sizes.", "Comparing means of two populations with smaller sample sizes."],
    ["F-Test", "Tests if variances among groups are equal.", "Testing for equal variances among groups."],
    ["Regression Analysis", "Analyzes the relationship between dependent and independent variables.", "Analyzing relationships between dependent and independent variables."],
    ["Correlation", "Measures the strength and direction of the linear relationship between two variables.", "Understanding linear relationships between two variables."],
    ["Bayesian Inference", "Updates probability estimates based on new evidence using Bayes' theorem.", "Updating probabilities with new evidence using Bayes' theorem."],
    ["Survival Analysis", "Analyzes the time until an event occurs and identifies factors affecting this time.", "Analyzing time until an event occurs and factors affecting it."],
    ["Time Series Analysis", "Analyzes data collected over time to identify trends and forecast future values.", "Forecasting future values based on historical time series data."],
    ["Monte Carlo Simulation", "Uses random sampling to estimate statistical properties and model uncertainty.", "Simulating scenarios to estimate statistical properties and risks."],
    ["Hierarchical Clustering", "Groups data into clusters based on similarity, forming a hierarchy.", "Grouping data into clusters based on similarity."],
    ["K-Means Clustering", "Partitions data into k distinct clusters based on feature similarity.", "Partitioning data into distinct clusters based on features."],
    ["Network Analysis", "Studies the relationships and interactions within networks.", "Studying interactions within networks."],
    ["Log-Rank Test", "Compares survival distributions of different groups to assess the impact of treatments.", "Comparing survival distributions across different groups."],
    ["GEE (Generalized Estimating Equations)", "Analyzes correlated data, especially for repeated measures or longitudinal data.", "Analyzing repeated measures or longitudinal data."],
    ["Mixed-Effects Models", "Models data with both fixed and random effects to account for hierarchical structures.", "Handling hierarchical data with fixed and random effects."],
    ["Quasi-Experiment", "Investigates causal relationships without random assignment, using naturally occurring groups.", "Evaluating causal relationships in naturally occurring groups."],
    ["Bootstrap Method", "Estimates distribution of a statistic by resampling with replacement from the data.", "Estimating distribution through resampling."],
    ["Jackknife Resampling", "Estimates the bias and variance of a statistic by systematically leaving out one observation at a time.", "Assessing bias and variance by systematically leaving out observations."],
    ["Lasso Regression", "Performs linear regression with L1 regularization to encourage sparsity in the model.", "Encouraging sparsity in regression models through L1 regularization."],
    ["Ridge Regression", "Performs linear regression with L2 regularization to address multicollinearity.", "Addressing multicollinearity through L2 regularization."],
    ["Principal Component Analysis (PCA)", "Reduces dimensionality of data while preserving variability.", "Reducing dimensionality while preserving data variability."],
    ["Factor Analysis", "Identifies underlying relationships between variables.", "Understanding underlying relationships between variables."],
    ["MANOVA", "Extends ANOVA to multiple dependent variables.", "Analyzing multiple dependent variables simultaneously."],
    ["General Linear Model (GLM)", "Models relationships between dependent and independent variables with various distributions.", "Modeling various distributions in regression analysis."],
    ["Mixed-Effects Models", "Models data with both fixed and random effects to account for hierarchical structures.", "Handling hierarchical data structures."],
    ["Time Series Forecasting", "Predicts future values based on historical time series data.", "Forecasting future values based on historical data."],
    ["Survival Analysis", "Analyzes time-to-event data and identifies factors affecting time to event.", "Analyzing time-to-event data and factors affecting it."],
    ["Quasi-Experiment", "Investigates causal relationships without random assignment, using naturally occurring groups.", "Evaluating causal effects without random assignment."],
    ["Bootstrap Method", "Estimates distribution of a statistic by resampling with replacement from the data.", "Estimating distribution through resampling."],
    ["Jackknife Resampling", "Estimates the bias and variance of a statistic by systematically leaving out one observation at a time.", "Assessing bias and variance by systematically leaving out observations."],
    ["Bayesian Inference", "Uses Bayes' theorem to update the probability of a hypothesis as more evidence becomes available.", "Updating probabilities with new evidence using Bayes' theorem."],
    ["Lasso Regression", "Performs linear regression with L1 regularization to encourage sparsity in the model.", "Encouraging sparsity in regression models through L1 regularization."],
    ["Ridge Regression", "Performs linear regression with L2 regularization to address multicollinearity.", "Addressing multicollinearity through L2 regularization."]
]

# Repeat the data to make it large
data.extend(data * 6)

# Create PDF document
pdf_file = "statistical_methods_report.pdf"
document = SimpleDocTemplate(pdf_file, pagesize=letter)

# Function to split data into chunks
def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# Split data into chunks (20 rows per chunk)
chunked_data = list(chunks(data, 20))

# Create elements list for the document
elements = []

# Create tables for each chunk and add a page break
for chunk in chunked_data:
    table = Table(chunk)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(table)
    elements.append(PageBreak())

# Build PDF
document.build(elements)
