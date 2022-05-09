# Nadj-Perge Group research data repository (with interactive Binder notebooks)

Binder link: [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/RMpolski/TBG_Data/main)

Data link: Caltech data doi [10.22002/D1.20151](https://dx.doi.org/10.22002/D1.20151). This needs to be downloaded to use the analysis notebooks. It will be downloaded by the Jupyter Notebooks in order to allow binder to work. Here is a link to the Caltech data saved repository [![DOI](https://data.caltech.edu/badge/487155960.svg)](https://data.caltech.edu/badge/latestdoi/487155960)

This dataset contains the experimental data and analysis from the following two papers:

Harpreet Singh Arora*, Robert Polski*, Yiran Zhang*, Alex Thomson, Youngjoon Choi, Hyunjin Kim, Zhong Lin, Ilham Zaky Wilson, Xiaodong Xu, Jiun-Haw Chu, Kenji Watanabe, Takashi Taniguchi, Jason Alicea, Stevan Nadj-Perge, "Superconductivity in metallic twisted bilayer graphene stabilized by WSe2", Nature 583, 379-384 (2020), https://doi.org/10.1038/s41586-020-2473-8, ArXiv: 2002.03003

and

Robert Polski*, Yiran Zhang*, Yang Peng, Harpreet Singh Arora1, Youngjoon Choi, Hyunjin Kim, Kenji Watanabe, Takashi Taniguchi, Gil Refael, Felix von Oppen, and Stevan Nadj-Perge, "Hierarchy of symmetry breaking correlated phases in twisted bilayer graphene", ArXiv: 

along with other analysis not included but along the same theme or same devices.

The raw data taking process and some notes are included in the folder ExperimentRuns, but it's unprocessed and only there for completeness. If you want to see the data in a more organized form and in a context that's easier to understand, see the notebooks in the AnalysisNotebooks folder. If viewing the notebooks, it helps to turn on collapsible headings (or download the @aquirdturtle/collapsible_headings widget if using JupyterLab). This makes the results much more organized and easy to look through. The two analysis notebooks have been run sequentially to check that they work.

The data is measured and stored using (the legacy version) of Qcodes (https://qcodes.github.io/Qcodes/). A basic fork of this (in the version that is known to work) +modifications we made is included here for running in Binder. Since the dataset (the main one taken from the Triton dilution fridge) is too large for a GitHub repository, it is stored in CaltechDATA (doi). It is downloaded and extracted at the beginning of each of the main two analysis notebook files. Also included in this repository is the data measured with a PPMS system since the dataset is much smaller.

The data measurements are stored in .dat files within their respective folders, often along with figure, organized by date and time. The .dat files are basically text files that have headers representing the measured quantities, and there is a .json snapshot with (most likely) the latest parameters from each instrument involved. The qcodes.load_data() function loads the data with parameters measured/set as arrays set as attributes of the dataset (so accessible with dataset.attribute). You can easily craft a non-qcodes function to extract the data, but it may require some rearranging of the arrays to get the shape right.

You can clone/fork the repository to explore the data more, or use the Binder link to explore without needing to worry about the python package dependencies.
