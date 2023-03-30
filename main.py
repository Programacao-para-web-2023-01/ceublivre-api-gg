from typing import Union
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector

cnx = mysql.connector.connect(user='root', database='ceublivre')
app = FastAPI()

class Users(BaseModel):
    id: int | None
    name: str
    mail: str

class Product(BaseModel):
    id: int | None
    name: str
    description: str
    category: str
    price: float

class wishlist(BaseModel):
    id: int | None
    cod_user: int
    cod_product: int

@app.get("/users")
async def get_users():
    cursor = cnx.cursor(dictionary=True)
    query = 'SELECT * FROM users'
    cursor.execute(query)

    return cursor.fetchall()

@app.post("/wishlistpost")
async def insert_product_wishlist(iduser: int, idproduct: int):
    cursor = cnx.cursor(dictionary=True)
    statement = "INSERT INTO wishlist(cod_product, cod_user)" \
                "VALUES (%s, %s)"
    val = (idproduct, iduser)
    #statement = "UPDATE products SET product_name = %s, product_description = %s, product_category = %s, product_price = %s "\
     #               "WHERE product_id = %s"



    cursor.execute(statement, val)
    cnx.commit()

    raise HTTPException(status_code=500, detail="Produto não encontrado ou ja na lista de desejo.")

    return {"detail": "Adicionado a lista de desejo com sucesso."}

