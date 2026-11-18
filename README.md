# AI / ML Portfolio

End-to-end projects across classical ML, time series, computer vision, NLP, LLMs, RAG, fine-tuning, agents, and MLOps. Each project lives in its own notebook under `notebooks/`.

The first 22 projects (`001-022`) are the most substantive — production-relevant LLM, agent, and MLOps work. Projects `023-111` are a broader exploration covering classical ML, CV, and NLP fundamentals.

## Data engineering (112+)

Production style pipelines, each in its own folder under `pipelines/` with tests, CI, infrastructure as code and a design doc.

| # | Project | Stack | Data |
|---|---------|-------|------|
| 112 | [Last mile lateness pipeline](pipelines/112_last_mile_lateness/) | S3, Lambda, Glue PySpark, Redshift Serverless, Terraform, data quality gates | Amazon Last Mile Routing (6,112 real routes) |

## Featured

These are the five I'd send a hiring manager first:

### 🥇 [008 — Medical LLM Fine-Tuning](notebooks/008_medical_llm_finetune/)
LoRA fine-tuning of TinyLlama on MedQuAD medical QA pairs. End-to-end PEFT pipeline with custom training loop (avoids `accelerate`/`launcher` pitfalls on CPU), evaluation against the base model on held-out questions, and Drive-mounted Colab paths for GPU runs. Honest framing about what changes (and doesn't) after light fine-tuning.

### 🥈 [019 — Natural Language to SQL](notebooks/019_nl_to_sql/)
NL-to-SQL on the Spider benchmark with execution-style evaluation. Includes a workaround for a corrupted local `tables.json` where the gold schema was rebuilt from `train_spider.json` gold SQL via FROM/JOIN parsing — a real engineering problem solved rather than papered over. Compares identifier-Jaccard and exact-match metrics.

### 🥉 [015 — AI Agent with Long-Term Memory](notebooks/015_long_term_memory_agent/)
LangChain agent with sliding-window short-term memory and a vector-store backed long-term memory. Includes a reflection step that decides what to commit to long-term storage. Honest about LangChain's compatibility quirks (`ConversationSummaryBufferMemory` failed on Gemini due to tiktoken; swapped for `ConversationBufferWindowMemory`).

### [012 — Fraud Detection Drift Monitor](notebooks/012_fraud_drift_monitor/)
Production-style monitoring around a fraud classifier: dataset and feature-level drift detection via Evidently, four synthetic drift scenarios (including a no-drift control), and honest reporting on which signals actually fire. The kind of work you'd inherit in a real MLOps role.

### [007 — Course Q&A Assistant (RAG)](notebooks/007_course_qa_assistant/)
RAG over course materials with retrieval evaluation (Recall@k, rank-of-correct) and a separate faithfulness judge. The judge prompt grades the answer text (not the context — a common bug we caught and fixed during review). Full pipeline runs offline-ish with local embeddings.

## All projects

Projects are numbered with a 3-digit zero-padded prefix so directory listings sort correctly.

### Core (001-022) — LLM, RAG, agents, MLOps

| # | Project | Topic | Size |
|---|---------|-------|------|
| 001 | [Mortgage Document Summarization](notebooks/001_mortgage_summarization/) | RAG / LLM | L |
| 002 | [Energy Market Clearing Price Forecasting](notebooks/002_energy_market_forecasting/) | Time Series | M |
| 003 | [IPL Score Prediction](notebooks/003_ipl_score_prediction/) | Classical ML | S |
| 004 | [Heart Disease Risk Prediction](notebooks/004_heart_disease_risk/) | Classification | S |
| 005 | [Diabetes Prediction](notebooks/005_diabetes_prediction/) | Classification | S |
| 006 | [Campus Store Inventory Management](notebooks/006_wollastons/) | SQL / DB | M |
| 007 | [Course Q&A Assistant](notebooks/007_course_qa_assistant/) ⭐ | RAG | M |
| 008 | [Medical LLM Fine-Tuning](notebooks/008_medical_llm_finetune/) ⭐ | LoRA / PEFT | L |
| 009 | [Multi-Document News Summarization](notebooks/009_news_summarization/) | NLP | M |
| 010 | [Hybrid Movie Recommender](notebooks/010_movie_recommender/) | Recommenders | S |
| 011 | [Student Dropout Risk Pipeline](notebooks/011_student_dropout/) | MLOps | L |
| 012 | [Fraud Detection Drift Monitor](notebooks/012_fraud_drift_monitor/) ⭐ | MLOps | M |
| 013 | [Multimodal Food Recognition](notebooks/013_food_recognition/) | CLIP / Vision | L |
| 014 | [AI Code Review Bot](notebooks/014_pr_review_bot/) | LLM Agents | M |
| 015 | [AI Agent with Long-Term Memory](notebooks/015_long_term_memory_agent/) ⭐ | Agents | L |
| 016 | [LLM-Powered Resume Screener](notebooks/016_resume_screener/) | LoRA / PEFT | L |
| 017 | [Structured Data Extraction](notebooks/017_structured_extraction/) | LoRA / PEFT | L |
| 018 | [Multi-Turn Conversational Agent](notebooks/018_multi_turn_agent/) | Agents | M |
| 019 | [Natural Language to SQL](notebooks/019_nl_to_sql/) ⭐ | QLoRA | L |
| 020 | [Customer Feedback Sentiment & Intent](notebooks/020_sentiment_intent/) | NLP | M |
| 021 | [LLM Eval and Red-Teaming Framework](notebooks/021_llm_eval_redteam/) | Eval | M |
| 022 | [Multimodal Product Classifier](notebooks/022_multimodal_product_classifier/) | CLIP / Vision | M |

### Beginner classification & regression (023-033)

| # | Project | Topic | Size |
|---|---------|-------|------|
| 023 | [Email Spam Detection](notebooks/023_email_spam_detection/) | Text Classification | S |
| 024 | [SMS Spam Detection](notebooks/024_sms_spam_detection/) | Text Classification | S |
| 025 | [Text Document Classification (20 Newsgroups)](notebooks/025_text_document_classification/) | Text Classification | S |
| 026 | [Iris Flowers Classification](notebooks/026_iris_classification/) | Classical ML | S |
| 027 | [Titanic Survival Prediction](notebooks/027_titanic_survival/) | Classical ML | S |
| 028 | [Wine Quality Prediction](notebooks/028_wine_quality/) | Regression | S |
| 029 | [Wine Type Prediction (red vs white)](notebooks/029_wine_type/) | Classification | S |
| 030 | [Boston / California Housing](notebooks/030_boston_housing/) | Regression | S |
| 031 | [Ames House Prices](notebooks/031_ames_house_prices/) | Regression | M |
| 032 | [Waiters' Tips Prediction](notebooks/032_waiters_tips/) | Regression | S |
| 033 | [Calories Burnt Prediction](notebooks/033_calories_burnt/) | Regression | S |

### Sentiment, customer, financial (034-044)

| # | Project | Topic | Size |
|---|---------|-------|------|
| 034 | [Restaurant Reviews Sentiment](notebooks/034_restaurant_reviews/) | NLP | S |
| 035 | [Flipkart Reviews Sentiment](notebooks/035_flipkart_sentiment/) † | NLP | S |
| 036 | [Twitter Sentiment Analysis](notebooks/036_twitter_sentiment/) | NLP | S |
| 037 | [Facebook / Social Media Sentiment](notebooks/037_facebook_sentiment/) † | NLP | S |
| 038 | [Fake News Detection (TF-IDF)](notebooks/038_fake_news_detection/) | NLP | S |
| 039 | [Customer Segmentation (K-Means)](notebooks/039_customer_segmentation/) † | Unsupervised | S |
| 040 | [Customer Churn (Telco)](notebooks/040_customer_churn/) † | Classification | S |
| 041 | [Loan Approval Prediction](notebooks/041_loan_approval/) † | Classification | S |
| 042 | [Loan Eligibility (SVM)](notebooks/042_loan_eligibility_svm/) † | Classification | S |
| 043 | [Disease Prediction from Symptoms](notebooks/043_disease_prediction_multilabel/) † | Classification | S |
| 044 | [Medical Insurance Cost](notebooks/044_medical_insurance_cost/) † | Regression | S |

### Medical, forecasting, handwritten digits (045-055)

| # | Project | Topic | Size |
|---|---------|-------|------|
| 045 | [Rainfall Prediction](notebooks/045_rainfall_prediction/) | Classification | S |
| 046 | [Breast Cancer Diagnosis (Wisconsin)](notebooks/046_breast_cancer_diagnosis/) | Classification | S |
| 047 | [Parkinson's Detection (voice features)](notebooks/047_parkinsons_detection/) | Classification | S |
| 048 | [Autism Screening (AQ-10)](notebooks/048_autism_screening/) | Classification | S |
| 049 | [Auto MPG / Fuel Efficiency](notebooks/049_fuel_efficiency/) | Regression | S |
| 050 | [Sales Forecast (SARIMA)](notebooks/050_sales_forecast/) † | Time Series | S |
| 051 | [Click-Through Rate Prediction](notebooks/051_click_through_rate/) † | Classification | S |
| 052 | [Used Cars Price Analysis](notebooks/052_used_cars_price/) † | Regression | S |
| 053 | [MNIST Handwritten Digits (CNN)](notebooks/053_mnist_digits_classification/) | CV | M |
| 054 | [MNIST Digits (sklearn classical)](notebooks/054_mnist_digits_sklearn/) | Classical ML | S |
| 055 | [Keras Sequential Intro (Fashion-MNIST)](notebooks/055_keras_sequential_intro/) | CV | S |

### Computer vision — intermediate (056-066)

| # | Project | Topic | Size |
|---|---------|-------|------|
| 056 | [Deep Learning OCR (digits + letters)](notebooks/056_deep_learning_ocr/) | CV | M |
| 057 | [Text Detection & Extraction](notebooks/057_text_detection_extraction/) † | CV / OCR | S |
| 058 | [Face Mask Detection](notebooks/058_face_mask_detection/) † | CV | S |
| 059 | [Dog Breed Classification (transfer learning)](notebooks/059_dog_breed_classification/) † | CV | S |
| 060 | [Flower Recognition](notebooks/060_flower_recognition/) † | CV | S |
| 061 | [Cat vs Dog (small CNN)](notebooks/061_cat_dog_cnn/) † | CV | S |
| 062 | [Traffic Signs Recognition](notebooks/062_traffic_signs/) † | CV | S |
| 063 | [CIFAR-10 Image Classification](notebooks/063_cifar10_classification/) | CV | M |
| 064 | [Multiclass Image Classification (architecture sweep)](notebooks/064_multiclass_image_classification/) | CV | M |
| 065 | [Image Caption Generator (BLIP)](notebooks/065_image_caption_generator/) | Multimodal | M |
| 066 | [Cartooning an Image (OpenCV)](notebooks/066_cartooning_image/) | CV | S |

### CV + audio + NLP toys (067-077)

| # | Project | Topic | Size |
|---|---------|-------|------|
| 067 | [Image Cartoonifier (advanced)](notebooks/067_image_cartoonifier_advanced/) | CV | S |
| 068 | [Count Faces in an Image](notebooks/068_count_faces/) | CV | S |
| 069 | [Count Objects (YOLO)](notebooks/069_count_objects/) | CV | S |
| 070 | [Age Detection from Face](notebooks/070_age_detection/) | CV | S |
| 071 | [Face & Hand Landmarks](notebooks/071_face_hand_landmarks/) † | CV | S |
| 072 | [Human Activity Recognition (UCI HAR)](notebooks/072_human_activity_recognition/) | Classification | S |
| 073 | [Speech Recognition Demo](notebooks/073_speech_recognition_demo/) | Audio | S |
| 074 | [Simple Voice Assistant](notebooks/074_voice_assistant/) | Audio / LLM | S |
| 075 | [Hate Speech Detection](notebooks/075_hate_speech_detection/) | NLP | S |
| 076 | [Sentiment with LSTM](notebooks/076_rnn_sentiment/) | NLP / Deep Learning | M |
| 077 | [Autocorrect (Norvig)](notebooks/077_autocorrect_feature/) | NLP | S |

### Forecasting & recommendation (078-088)

| # | Project | Topic | Size |
|---|---------|-------|------|
| 078 | [TED Talks Recommender](notebooks/078_ted_talks_recommender/) † | Recommenders | S |
| 079 | [Emotion-Based Movie Recommender](notebooks/079_emotion_movie_recommender/) | Recommenders | S |
| 080 | [Credit Card Fraud Detection](notebooks/080_credit_card_fraud/) † | Classification | M |
| 081 | [Online Payment Fraud](notebooks/081_payment_fraud_online/) † | Classification | S |
| 082 | [Inventory Demand Forecast](notebooks/082_inventory_demand_forecast/) † | Time Series | S |
| 083 | [Vehicle Count Prediction](notebooks/083_vehicle_count_prediction/) † | CV / Regression | S |
| 084 | [Air Quality Index (GBM)](notebooks/084_air_quality_index/) | Regression | S |
| 085 | [Air Quality (Neural Net)](notebooks/085_air_quality_nn/) | Regression | S |
| 086 | [Ola Bike Demand Forecast](notebooks/086_ola_bike_demand/) | Time Series | S |
| 087 | [Stock Price Prediction (LSTM)](notebooks/087_stock_price_lstm/) | Time Series | M |
| 088 | [Stock Price Prediction (ARIMA)](notebooks/088_stock_price_arima/) | Time Series | S |

### Crypto, license plates, BERT (089-099)

| # | Project | Topic | Size |
|---|---------|-------|------|
| 089 | [Bitcoin Price Prediction](notebooks/089_bitcoin_price_prediction/) | Time Series | M |
| 090 | [Dogecoin Price Prediction](notebooks/090_dogecoin_price_prediction/) | Time Series | S |
| 091 | [Microsoft Stock Prediction](notebooks/091_microsoft_stock_prediction/) | Time Series | M |
| 092 | [Stock Price Direction (classification)](notebooks/092_stock_price_direction/) | Classification | S |
| 093 | [Share Price Long-Horizon Forecast (Prophet)](notebooks/093_share_price_forecasting_longterm/) | Time Series | S |
| 094 | [Employee Management System (CRUD / SQL)](notebooks/094_employee_management_system/) | SQL / DB | S |
| 095 | [License Plate Recognition (OCR)](notebooks/095_license_plate_recognition/) † | CV / OCR | S |
| 096 | [Car License Plate Pipeline (CNN)](notebooks/096_car_license_plate_pipeline/) † | CV | S |
| 097 | [Fake News Detection (DistilBERT)](notebooks/097_fake_news_bert/) † | NLP / Transformers | M |
| 098 | [Next Sentence Prediction (BERT)](notebooks/098_next_sentence_prediction/) | NLP / Transformers | S |
| 099 | [BERT Fine-Tune for Sentiment](notebooks/099_bert_finetune_sentiment/) † | NLP / Transformers | M |

### Advanced deep learning (100-111)

| # | Project | Topic | Size |
|---|---------|-------|------|
| 100 | [BERT Sentiment (frozen embeddings)](notebooks/100_bert_sentiment_classification/) † | NLP / Transformers | M |
| 101 | [ResNet From Scratch (CIFAR-10)](notebooks/101_resnet_from_scratch/) | Deep Learning | M |
| 102 | [Skin Cancer Detection*](notebooks/102_skin_cancer_detection/) | Medical CV | S |
| 103 | [Lung Cancer Prediction*](notebooks/103_lung_cancer_detection/) | Medical | S |
| 104 | [Pneumonia X-Ray Detection*](notebooks/104_pneumonia_detection/) | Medical CV | S |
| 105 | [COVID-19 X-Ray Detection*](notebooks/105_covid_xray_detection/) | Medical CV | S |
| 106 | [Image Segmentation (U-Net)](notebooks/106_image_segmentation_unet/) † | Deep Learning | M |
| 107 | [B&W → Color (Autoencoder)](notebooks/107_image_colorization/) | Deep Learning | M |
| 108 | [Heart Disease ANN (follow-up to 004)](notebooks/108_heart_disease_ann/) | Deep Learning | S |
| 109 | [Spaceship Titanic (Kaggle)](notebooks/109_spaceship_titanic/) † | Classical ML | S |
| 110 | [Zillow Home Value (Zestimate)](notebooks/110_zillow_zestimate/) | Regression | M |
| 111 | [Box Office Revenue](notebooks/111_box_office_revenue/) † | Regression | S |

## Setup

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your API keys before running RAG or LLM notebooks. Most non-LLM notebooks run without external services.

## Data

Datasets live in `data/` (one folder per project). Built-in datasets (`sklearn`, `torchvision`, `seaborn`, `nltk`) download on first run and don't need a local folder. Larger files are gitignored.

## Honest disclosures

A portfolio this size deserves some transparency about what's real and what isn't.

- **⭐ Featured projects** are the ones I'd send first. The full list exists because I wanted breadth across classical ML, CV, NLP, and LLM work; the strongest material is concentrated in `001-022`.
- **† Synthetic data.** Projects marked with a dagger use synthetic stand-in data because the real dataset was gated (Kaggle competitions), large (medical imaging), or not freely mirrored (e.g., Flipkart reviews). Each affected notebook says so in its markdown. These are pipeline / methodology demos, not benchmarks.
- **\* Medical CV (102, 104, 105)** specifically use synthetic image data (real datasets like HAM10000 / ChestX-ray / COVID-19 Radiography require accounts and licenses). These notebooks demonstrate the modeling pipeline only — they are not clinical models and should not be read as such.
- **Stock / crypto projects (087-093)** are time-series methodology demos. They do not claim to predict prices or earn returns; markdown is honest that beating naive baselines is hard at the horizons covered.
- **CV training budgets** are small (1-3 epochs on CPU) to keep notebook execution under a few minutes. Real benchmarking would need GPU and longer schedules.
- **Project 094 (Employee Management System)** is a database CRUD assignment, not ML — it's included for completeness because it was a class deliverable.
- **Projects 053-056 cover handwritten digits** at increasing sophistication (sklearn classical → small CNN → deeper CNN with letters); kept separate to show the progression.

If you only have time for a few, start with the **Featured** five above.
