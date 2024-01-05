import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
import torch.optim as optim
from sklearn.model_selection import train_test_split
from transformers import BertModel


# Define a custom dataset
class ReviewDataset(Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx], dtype=torch.float)
        return item

    def __len__(self):
        return len(self.labels)


# Define the model
class RatingRegressor(nn.Module):
    def __init__(self):
        super(RatingRegressor, self).__init__()
        self.bert = BertModel.from_pretrained("bert-base-uncased")
        for param in self.bert.parameters():
            param.requires_grad = False
        self.regressor = nn.Linear(self.bert.config.hidden_size, 4)

    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        pooled_output = outputs.pooler_output
        return self.regressor(pooled_output)


# Engine for training and inference
class TextScalerEngine:
    def __init__(self, dataframe, model, tokenizer):
        self.dataframe = dataframe
        self.tokenizer = tokenizer
        self.model = model

        # Tokenize the text
        self.encodings = tokenizer.batch_encode_plus(
            self.dataframe["text"].tolist(),
            padding="longest",
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )

        # Extract labels
        self.labels = self.dataframe[
            [
                "average_menu",
                "average_taste",
                "average_indoor_atmosphere",
                "average_outdoor_atmosphere",
            ]
        ].values

    def create_data_loaders(self, test_size=0.1, batch_size=16):
        # Train-test split
        train_encodings, val_encodings, train_labels, val_labels = train_test_split(
            self.encodings, self.labels, test_size=test_size
        )

        # Create datasets
        train_dataset = ReviewDataset(train_encodings, train_labels)
        val_dataset = ReviewDataset(val_encodings, val_labels)

        # Create data loaders
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size)
        return train_loader, val_loader

    def train(self, train_loader, val_loader, epochs=3):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = self.model.to(device)
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=2e-5)

        for epoch in range(epochs):
            self.model.train()
            for batch in train_loader:
                optimizer.zero_grad()
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["labels"].to(device)
                outputs = self.model(input_ids, attention_mask)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
            print(f"Epoch {epoch + 1}/{epochs} Loss: {loss.item()}")

            # Evaluate on the validation set
            self.model.eval()
            total_loss = 0
            with torch.no_grad():
                for batch in val_loader:
                    input_ids = batch["input_ids"].to(device)
                    attention_mask = batch["attention_mask"].to(device)
                    labels = batch["labels"].to(device)
                    outputs = self.model(input_ids, attention_mask)
                    loss = criterion(outputs, labels)
                    total_loss += loss.item()
            print(f"Validation Loss: {total_loss / len(val_loader)}")
