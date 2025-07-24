# Hrone_Backend
# 🛍️ FastAPI Products & Orders API

A lightweight FastAPI backend to manage **products** and **orders**, built using **MongoDB** as the database.

---

## 🚀 Features

- ✅ Create and list products with name, price ,sizes{size and quantity}
- ✅ Create and list user orders with product details
- ✅ Built with FastAPI
- ✅ MongoDB used as the database

---

## 📂 Project Structure

```
.
├── main.py # Main FastAPI application
├── requirements.txt    # Python dependencies
└── README.md
```

---

## 🔧 Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up MongoDB

Create a `.env` file with your MongoDB URI:

```
MONGO_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
```

Use this in `index.py` with `os.getenv("MONGO_URI")`.

### 4. Run locally

```bash
uvicorn api.index:app --reload
```

---

## 🧪 Example Routes

### ➕ Create Product

`POST /products`

```json
{
  "name": "T-shirt",
  "price": "499",
  "sizes": {
    "size": "M",
    "quantity": "10"
  }
}
```

### 📦 List Products

`GET /products`

### 🧾 Create Order

`POST /orders`

```json
{
  "userId": "12345",
  "items": [
    { "productId": "abc123", "qty": 2 }
  ]
}
```

### 📋 Get User Orders

`GET /orders/12345`

---





