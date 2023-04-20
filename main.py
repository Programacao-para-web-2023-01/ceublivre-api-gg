from typing import Union, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to_email: str, wishlist_id: int, server_url: str):
    try:
        # Gerar URL da lista de desejos
        wishlist_url = f"{server_url}/wishlist?id={wishlist_id}"

        # Configurar mensagem de e-mail
        message = MIMEMultipart()
        message["Subject"] = "Lista de Desejos"
        message["From"] = "geraldopjc@gmail.com"
        message["To"] = to_email
        text = f"Olá, segue o link da sua lista de desejos: {wishlist_url}"
        message.attach(MIMEText(text, "plain"))

        # Configurar servidor SMTP
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login("geraldopjc@gmail.com", "30125047GGdf")

        # Enviar e-mail
        server.sendmail("geraldopjc@gmail.com", to_email, message.as_string())
        server.quit()

        return {"detail": f"E-mail enviado com sucesso para {to_email}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar e-mail: {e}")

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

def get_id_wishlist(iduser):
    cursor = cnx.cursor(dictionary=True)
    select_statement = "SELECT user_name, GROUP_CONCAT(product_name) AS holder "\
                        "FROM products JOIN wishlist ON product_id=cod_product "\
                        "JOIN users ON user_id=cod_user "\
                        "WHERE user_id = %s "\
                        "GROUP BY user_name"
    val = (iduser,)
    cursor.execute(select_statement, val)
    result = cursor.fetchall()
    return result


@app.get("/users")
async def get_users():
    cursor = cnx.cursor(dictionary=True)
    query = 'SELECT * FROM users'
    cursor.execute(query)

    return cursor.fetchall()

@app.get("/userwishlist")
async def get_user_wishlist(iduser: int):
    result = get_id_wishlist(iduser)
    if not result:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado na lista de desejos.")
    else:
        return result

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



@app.delete("/wishlistdel")
async def delete_product_wishlist(wish_id: int):
    try:
        cursor = cnx.cursor(dictionary=True)
        select_statement = "SELECT * FROM wishlist WHERE id_wishlist = %s"
        val = (wish_id,)
        cursor.execute(select_statement, val)
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Produto não encontrado na lista de desejos.")
        else:
            delete_statement = "DELETE FROM wishlist WHERE id_wishlist = %s"
            cursor.execute(delete_statement, val)
            cnx.commit()
            return {"detail": "Produto excluído com sucesso da lista de desejos."}
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Erro ao excluir produto da lista de desejos: {err.msg}")

from typing import Optional

@app.post("/wishlistshare")
async def share_wishlist(email: str, wish_id: int, subject: Optional[str] = "Lista de Desejos Compartilhada"):
    try:
        cursor = cnx.cursor(dictionary=True)
        select_user_statement = "SELECT * FROM users WHERE user_mail = %s"
        val = (email,)
        cursor.execute(select_user_statement, val)
        user_result = cursor.fetchone()
        if not user_result:
            raise HTTPException(status_code=404, detail="Usuário com o e-mail fornecido não encontrado.")
        else:
            if 'user_id' in user_result:
                update_statement = "UPDATE wishlist SET cod_user = %s WHERE id_wishlist = %s"
                val = (user_result['user_id'], wish_id)
                cursor.execute(update_statement, val)
                cnx.commit()
                # chamando a função send_email para enviar o e-mail
                wishlist_items = get_id_wishlist(user_result['user_id'])
                if wishlist_items:
                    products = ", ".join([item['holder'] for item in wishlist_items])
                else:
                    products = "Nenhum produto encontrado na lista de desejos."
                message = f"Olá, segue abaixo o link para acessar a sua lista de desejos: http://localhost/userwishlist?iduser={user_result['user_id']}\nProdutos: {products}"
                send_email(email, subject, message)
                return {"detail": f"Lista de desejos compartilhada com sucesso com o e-mail {email}"}
            else:
                raise HTTPException(status_code=500, detail="Campo 'id' não encontrado no resultado da consulta.")
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Erro ao compartilhar lista de desejos: {err.msg}")
