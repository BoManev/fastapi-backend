from transformers import BertTokenizer
from api.core.search_engine.text_scaler_engine import RatingRegressor, TextScalerEngine

tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
model = RatingRegressor()

engine = TextScalerEngine(imputed_df, model, tokenizer)
train_loader, val_loader = engine.create_data_loaders()
engine.train(train_loader, val_loader)
