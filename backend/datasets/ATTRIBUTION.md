# Dataset sources

LEAP's runtime datasets are derived from real public teaching and research datasets. The CSV files preserve only the columns needed by each guided task.

- `sentiment_labelled_sentences_uci_v2.csv`: Kotzias, D. (2015), *Sentiment Labelled Sentences*, UCI Machine Learning Repository, DOI `10.24432/C57604`, CC BY 4.0. Contains all 3,000 labeled Amazon, IMDb, and Yelp sentences.
- `ames_housing_v2.csv`: De Cock, D. (2011), *Ames, Iowa: Alternative to the Boston Housing Data as an End of Semester Regression Project*, Journal of Statistics Education 19(3). Contains all 2,930 property sales with five lesson-facing fields derived from the source columns.
- `optical_digits_uci_v2.csv`: Alpaydin, E. and Kaynak, C. (1998), *Optical Recognition of Handwritten Digits*, UCI Machine Learning Repository, DOI `10.24432/C50P49`, CC BY 4.0. Contains all 5,620 examples represented as 8×8 pixel-block intensity values.

The preparation script is `backend/scripts/prepare_real_datasets.py`. Source archives are downloaded to `/tmp/leap-real-datasets` before running it.
