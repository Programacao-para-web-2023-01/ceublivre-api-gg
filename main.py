from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from deta import Deta

app = FastAPI()

deta = Deta('e05tW9KfFXAh_1X6VitLLEkY14CfB4eNXwHWStznACk91')
dbUsers = deta.Base("Users") #Base temp. de usuários
dbProducts = deta.Base("Products") #Base de produtos ativos temp.
dbWishlist = deta.Base("wishlists") #base de wishlists(?)

drive = deta.Drive("Images") # Drive de Imagens (ativos)
dbInactiveProducts = deta.Base("ProductDatabase")# Base de produtos(Inativos)


class Users(BaseModel):
    key: str | None
    name: str
    mail: str


class Product(BaseModel):
    key: str | None
    name: str
    description: str
    category: str
    price: float

class Wishlist(BaseModel):
    key: str | None
    cod_user: str
    cod_product: str




@app.get("/users")
async def get_users():
    result = dbUsers.fetch()
    return result

@app.post("/users")
async def register_user(user: Users):
    new_item = {
        "name": user.name,
        "mail": user.mail
    }
    result = dbUsers.insert(new_item)
    if result.get("failed"):
        raise HTTPException(status_code=404, detail="Falhao ao inserir, olha essa porra ai.")
    else:
        return {"detail": "Adicionado a lista de usuários com sucesso."}



@app.get("/products")
async def get_product():
    result = dbProducts.fetch().items
    return result

@app.post("/products")
async def insert_product(product: Product):
    new_item = {
        "name": product.name,
        "description": product.description,
        "category": product.category,
        "price": product.price
    }
    result = dbProducts.insert(new_item)
    if result.get("failed"):
        raise HTTPException(status_code=404, detail="Falhao ao inserir, olha essa porra ai.")
    else:
        return {"detail": "Adicionado a lista de produtos com sucesso."}


###################################################################################################################################################################################################################################################################
###################################################################################################################################################################################################################################################################

@app.get("/wishlist/{id}")
async def get_wishlist_by_id(id: str):
    wishlist_items = dbWishlist.fetch({"cod_user": id}).items
    if not wishlist_items:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado na lista de desejos do usuário.")
    keys = [item["cod_product"] for item in wishlist_items]
    products = []
    for key in keys:
        product = dbProducts.get(key)
        if product:
            product_info = {
                "nome": product["name"],
                "descrição": product["description"],
                "categoria": product["category"],
                "preço": product["price"]
            }
            products.append(product_info)

    if not products:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado na wishlist.")

    return products





@app.get("/wishlist")
async def get_user_wishlist(user_name: str):
    user = dbUsers.fetch({"name": user_name}).items
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    wishlist_items = dbWishlist.fetch({"cod_user": user[0]["key"]}).items
    if not wishlist_items:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado na lista de desejos do usuário.")

    product_keys = [item["cod_product"] for item in wishlist_items]

 # Consulta para obter os nomes dos produtos com base nas chaves - erroddd
    products = []
    for key in product_keys:
        product = dbProducts.get(key)
        if product:
            product_info ={
                "nome": product["name"],
                "descrição": product["description"],
                "categoria" : product["category"],
                "preço": product["price"]
            }
            products.append(product_info)
    if not products:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado na wishlist.")


    return products




@app.post("/wishlist")
async def insert_product_wishlist(iduser: str, idproduct: str):
    new_item = {
        "cod_product": idproduct,
        "cod_user": iduser
    }
    result = dbWishlist.insert(new_item)
    if result.get("failed"):
        raise HTTPException(status_code=500, detail="Produto não encontrado ou já na lista de desejos.")
    else:
        return {"detail": "Adicionado a lista de desejo com sucesso."}

@app.delete("/wishlist")
async def delete_product_wishlist_by_wid(wish_id: str):
    try:
        result = dbWishlist.get(wish_id)
        if not result:
            return {"detail": "Código de Produto não encontrado na lista de desejos."}
        if result:
            dbWishlist.delete(wish_id)
            return {"detail": "Código de Produto excluído com sucesso da lista de desejos."}
        else:
            raise HTTPException(status_code=404, detail=f"Erro ao excluir produto da lista de desejos: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao excluir produto da lista de desejos: {str(e)}")



@app.post("/wishlistshare")
async def share_wishlist(email: str, wish_id: str):
    try:
        select_user = db.query({"mail": email}).fetch()
        if not select_user:
            raise HTTPException(status_code=404, detail="Usuário com o e-mail fornecido não encontrado.")
        else:
            user_id = select_user[0]["id"]
            update_result = db.update({"cod_user": user_id}, {"$push": {"wishlist": wish_id}})
            if update_result.get("failed"):
                raise HTTPException(status_code=500, detail="Erro ao compartilhar lista de desejos.")
            else:
                return {"detail": f"Lista de desejos compartilhada com sucesso com o e-mail {email}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao compartilhar lista de desejos: {str(e)}")
