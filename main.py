from fastapi import FastAPI, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson import ObjectId 


app = FastAPI(
    title="Products and Orders API with MongoDB", 
    description="A simple API task which manage products and orders, stored in MongoDB ." 
)

# MongoDB connection 
uri = "mongodb+srv://vijaykumarstage:KaxtyDoRIjtYMX4I@cluster0.3efaagg.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(f"MongoDB connection error: {e}")

# Define the database and collections
db = client.products_db 
products_collection = db.products
orders_collection = db.orders 

class ProductSize(BaseModel):
    size: str
    quantity: str


class ProductIn(BaseModel):
    name: str
    price: str
    sizes: ProductSize
class ProductOut(ProductIn):
    id: Optional[str] = Field(alias="_id")

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

class Pagination(BaseModel):
    next: Optional[int] = None
    limit: Optional[int] = None
    previous: Optional[int] = None


class ProductsResponse(BaseModel):
    data: List[ProductOut]
    page: Pagination


class OrderItem(BaseModel):
    productId: str
    qty: int 

class OrderIn(BaseModel):
    userId: str
    items: List[OrderItem]


class OrderOut(BaseModel):
    id: Optional[str] = Field(alias="_id") # MongoDB's _id for the order

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class OrderProductDetails(BaseModel):
    id: str = Field(alias="_id") # Product ID
    name: str
 
    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class OrderItemDetails(BaseModel):
    productDetails: OrderProductDetails
    qty: int


class OrderListOut(BaseModel):
    id: str = Field(alias="_id") # Order ID
    userId: str
    items: List[OrderItemDetails]
    total: float = 0.0 

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class OrdersResponse(BaseModel):
    data: List[OrderListOut]
    page: Pagination


@app.post(
    "/products",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
    description="Adds a new product to the MongoDB database and returns only the ID."
)
async def create_product(product: ProductIn):
    product_dict = product.model_dump(by_alias=True)
    result = products_collection.insert_one(product_dict)

    if result.inserted_id:
        return {"id": str(result.inserted_id)}
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create product")

@app.get(
    "/products",
    response_model=ProductsResponse,
    summary="Get all products with filtering, searching, and pagination",
    description="Retrieves a list of all products currently stored in the MongoDB database, with optional filters for name and size, and pagination."
)
async def get_products(
    name: Optional[str] = Query(None, description="Partial search for product name (case-insensitive, regex supported)."),
    size: Optional[str] = Query(None, description="Filter products by a specific size."),
    limit: int = Query(10, ge=1, description="Number of documents to return per page."),
    offset: int = Query(0, ge=0, description="The number of documents to skip while paginating (sorted by _id).")
):
    
    query_filter: Dict[str, Any] = {}

    if name:
        query_filter["name"] = {"$regex": name, "$options": "i"}
    
    if size:
        query_filter["sizes.size"] = size

    total_products = products_collection.count_documents(query_filter)

    products_cursor = products_collection.find(query_filter).skip(offset).limit(limit)

    products = []
    for doc in products_cursor:
        doc["_id"] = str(doc["_id"])
        products.append(ProductOut(**doc))

    next_offset = offset + limit if (offset + limit) < total_products else None
    previous_offset = offset - limit if offset - limit >= 0 else None
    
    pagination_limit = limit

    return ProductsResponse(
        data=products,
        page=Pagination(
            next=next_offset,
            limit=pagination_limit,
            previous=previous_offset
        )
    )

@app.post(
    "/orders",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED, 
    summary="Create a new order",
    description="Creates a new order with a user ID and a list of product items."
)
async def create_order(order: OrderIn):
    
    order_dict = order.model_dump(by_alias=True)
    
    result = orders_collection.insert_one(order_dict)
    
    new_order = orders_collection.find_one({"_id": result.inserted_id})
    
    if new_order:
        new_order["_id"] = str(new_order["_id"])
        return OrderOut(**new_order)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create order")

@app.get(
    "/orders/{user_id}",
    response_model=OrdersResponse, 
    summary="Get orders for a specific user with pagination",
    description="Retrieves a list of orders for a given user, with optional pagination. Includes product details for each item."
)
async def get_orders_by_user(
    user_id: str, 
    limit: int = Query(10, ge=1, description="Number of documents to return per page."),
    offset: int = Query(0, ge=0, description="The number of documents to skip while paginating (sorted by _id).")
):
   
    query_filter: Dict[str, Any] = {"userId": user_id}

    total_orders = orders_collection.count_documents(query_filter)

    
    pipeline = [
        {"$match": query_filter}, 
        {"$sort": {"_id": 1}}, 
        {"$skip": offset},
        {"$limit": limit},
        {"$unwind": "$items"}, 
        {
            "$lookup": {
                "from": products_collection.name, 
                "localField": "items.productId",
                "foreignField": "_id",
                "as": "items.productDetails"
            }
        },
        {"$unwind": "$items.productDetails"}, 
        {
            "$addFields": { 
                "items.productDetails.price_float": {
                    "$toDouble": "$items.productDetails.price"
                },
                "items.itemTotal": {
                    "$multiply": ["$items.qty", {"$toDouble": "$items.productDetails.price"}]
                }
            }
        },
        {
            "$group": { 
                "_id": "$_id",
                "userId": {"$first": "$userId"},
                "items": {
                    "$push": {
                        "productDetails": {
                            "_id": "$items.productDetails._id",
                            "name": "$items.productDetails.name",
                            "price": "$items.productDetails.price" 
                        },
                        "qty": "$items.qty"
                    }
                },
                "total": {"$sum": "$items.itemTotal"} 
            }
        },
        {"$project": { 
            "_id": 1,
            "userId": 1,
            "items": {
                "$map": {
                    "input": "$items",
                    "as": "item",
                    "in": {
                        "productDetails": {
                            "id": {"$toString": "$$item.productDetails._id"}, 
                            "name": "$$item.productDetails.name"
                            
                        },
                        "qty": "$$item.qty"
                    }
                }
            },
            "total": 1
        }}
    ]

    orders_cursor = orders_collection.aggregate(pipeline)

    orders = []
    for doc in orders_cursor:
        
        orders.append(OrderListOut(**doc))

    next_offset = offset + limit if (offset + limit) < total_orders else None
    previous_offset = offset - limit if offset - limit >= 0 else None
    
    pagination_limit = limit

    return OrdersResponse(
        data=orders,
        page=Pagination(
            next=next_offset,
            limit=pagination_limit,
            previous=previous_offset
        )
    )
