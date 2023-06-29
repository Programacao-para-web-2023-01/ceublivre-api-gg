from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from deta import Deta
import smtplib
from email.mime.text import MIMEText

app = FastAPI()

# Configuração do CORS
origins = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
##########################

deta = Deta('e05tW9KfFXAh_1X6VitLLEkY14CfB4eNXwHWStznACk91')
dbUsers = deta.Base("Users") #Base temp. de usuários
dbProducts = deta.Base("Products") #Base de produtos ativos temp.
dbWishlist = deta.Base("wishlists") #base de wishlists(?)

drive = deta.Drive("Images") # Drive de Imagens (ativos)
dbInactiveProducts = deta.Base("ProductDatabase")# Base de produtos(Inativo)


class Users(BaseModel):
    key: str | None
    name: str
    mail: str


class Product(BaseModel):
    name: str
    description: str
    category: str
    price: float
    stock: int

class Updated_product(BaseModel):
    name: str
    description: str
    category: str
    price: float

class Wishlist(BaseModel):
    key: str | None
    cod_user: str
    cod_product: str
    price_at_time: float
    stock: int



def check_wishlist_on_update_price(product: Product): #recebe o produto que acabou de ser atualizado pelo vendedor
    wishlist_items = dbWishlist.fetch().items #recebe a db de wishlists
    users_to_notify = [] #Definido lista dos usuários que receberação notificação

    for item in wishlist_items: #percorre a lista a procura de um match com o price definido menor que o price_at_time
        if item["cod_product"] == product.key and item["price_at_time"] > product.price:
            get_user_name = dbUsers.get(item["cod_user"])
            users_to_notify.append(get_user_name["name"]) #junto os items na lista

    if users_to_notify:
        raise HTTPException(status_code=400, detail=f"Os seguintes usuários receberão notificação: {', '.join(users_to_notify)}")

    return True #retorna nada, caso não encontre match



@app.post("/teste da notificação")
async def on_updat(product: Product):
    check_wishlist_on_update_price(product)
    #implementa e-mail




###################################################################################################################################################################################################################################################################
###################################################################################################################################################################################################################################################################
#rotas essênciais temporárias

@app.post("/user_authentication")
async def auth(key: str):
    user_auth = dbUsers.fetch({"key": key})
    if user_auth.items:
        return True
    raise HTTPException(status_code=404, detail="Id de uusuuário não encontrado")

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
async def get_products():
    result = dbProducts.fetch().items
    return result

@app.post("/products")
async def insert_product(product: Product):
    new_item = {
        "key": product.name+"_key",
        "name": product.name,
        "description": product.description,
        "category": product.category,
        "price": product.price,
        "stock": product.stock
    }
    result = dbProducts.insert(new_item)
    if result.get("failed"):
        raise HTTPException(status_code=404, detail="Falhao ao inserir, olha essa porra ai.")
    else:
        return {"detail": "Adicionado a lista de produtos com sucesso."}

@app.put("/products/{idproduct}")
async def update_product(idproduct: str, updated_product: Updated_product):
    # Verificar se o produto existe
    product = dbProducts.fetch({"key": idproduct})
    if not product:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    # Atualizar os dados do produto
    updated_product_dict = updated_product.dict()
    dbProducts.update(updated_product_dict, key=idproduct)

    return {"detail": "Produto atualizado com sucesso."}

@app.post("/product_img/{idproduct}")
async def insert_img(id: str):
    product = dbProducts.get({"key": id})

    if product:
        product_name = product["name"]
        img_name = f"{product_name}.png"
        path = f"/imgs/{img_name}"
        with open(path, 'rb') as file:
            file_test = file.read()
            deta_project.put(file_test,img_name)
            return {"detail": "Imagem inserida para o produto"}
    raise HTTPException(status_code=404, detail="Produto não encontrado.")
###################################################################################################################################################################################################################################################################
###################################################################################################################################################################################################################################################################
#Rotas wishlist

@app.get("/wishlist/{id}") #melhor implementavél 
async def get_wishlist_by_id(id: str):
    check_u = dbUsers.get(id) #verificação da existencia do usuário
    if not check_u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    wishlist_items = dbWishlist.fetch({"cod_user": id}).items  #verificação da existencia de wishlist do usuário e definido lista dos valores
    if not wishlist_items:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado na lista de desejos do usuário.")
    
    products = [] #definir lista de dict vázio
    for item in wishlist_items:     #para cada chave, recupera os dados do produto na tabelaa de produtos
        product = dbProducts.get(item["cod_product"])  
        if product:
            product_info = {      #definido formato das info do item
                "id": item["key"],   
                "cod_de_barras": product["key"],                   
                "name": product["name"],
                "description": product["description"],
                "category": product["category"],
                "price": product["price"],
                "stock": product["stock"]
            }
            products.append(product_info) #adicionado os items como dicionario a lista

    if not products:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado na wishlist.")

    return products





@app.get("/wishlist")
async def get_user_wishlist(user_name: str):
    user = dbUsers.fetch({"name": user_name}).items #verificação da existencia do usuário
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    wishlist_items = dbWishlist.fetch({"cod_user": user[0]["key"]}).items #verificação da existencia de wishlist do usuário
    if not wishlist_items:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado na lista de desejos do usuário.")

    product_keys = [item["cod_product"] for item in wishlist_items]

 # Consulta para obter os nomes dos produtos com base nas chaves
    products = [] #definir dicionario vázio
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

    check_p_key = dbProducts.get(idproduct) #validação do produto na lista de produtos
    check_u_key = dbUsers.get(iduser) #validação do usuário
    check_wishlist = dbWishlist.fetch({"cod_user": iduser, "cod_product": idproduct}).items #validação do produto x usuário na lista -- fetch pois é uma lista sem items dict
    #Verificação boleana dos checks
    if not check_p_key:
        raise HTTPException(status_code=404, detail="Produto não encontrado. Verifique Codigo de produto e tente novamente.")
    if not check_u_key:
        raise HTTPException(status_code=404, detail="Falha ao identificar usuário. Verifique ID Login.")
    if check_wishlist:
        raise HTTPException(status_code=404, detail="Produto ja na lista de desejos do usuário.")

    new_item = {
        "cod_user": iduser,
        "cod_product": idproduct,
        "price_at_time": check_p_key["price"]
    }
    dbWishlist.insert(new_item) #inserir produto na wishlist
    return {"detail": "Adicionado a lista de desejo com sucesso."}
    #A fazer:
    #Adicionar marcação se produto está disponivel ou não para habilitar notificação
    #Marcar preço no momento de inserido na lista para habilitar notificação de preço

@app.delete("/wishlist")
async def delete_product_wishlist_by_wid(wish_id: str):
    try:
        result = dbWishlist.get(wish_id)
        if not result:
            return {"detail": "Falha ao localizar produto na lista de desejos."}
        if result:
            dbWishlist.delete(wish_id)
            return {"detail": "Produto excluído com sucesso da lista de desejos."}
        else:
            raise HTTPException(status_code=404, detail=f"Erro ao excluir produto da lista de desejos: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao excluir produto da lista de desejos: {str(e)}")





###################################################################################################################################################################################################################################################################
###################################################################################################################################################################################################################################################################


@app.post("/wishlistshare")
async def share_wishlist(wishlist: Wishlist, email: str):
    user = dbUsers.get(wishlist.cod_user)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    recipient = dbUsers.fetch({"mail": email}).items
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient user not found.")
    recipient_user = recipient[0]
    updated_item = {
        **wishlist.dict(),
        "cod_user": recipient_user["key"]
    }
    result = dbWishlist.update(updated_item)
    if result.get("failed"):
        raise HTTPException(status_code=404, detail="Failed to share wishlist.")
    else:
        return {"detail": "Wishlist shared successfully."}

""
def get_previous_price(product_key: str):
    previous_price = dbInactiveProducts.get(product_key)
    return previous_price.get("price") if previous_price else 0.0

def send_notification(email: str, product_name: str):
    subject = "Notificação de Redução de Preço"
    message = f"O preço do produto {product_name} foi reduzido."
    send_email(email, subject, message)

def send_notification_disponibility(email: str, product_name: str):
    subject = "Notificação de Disponibilidade de Produto"
    message = f"O produto {product_name} está disponível agora."
    send_email(email, subject, message)

@app.post("/e-mail teste")
def send_email(email_sender: str, email_receiver: str, subject: str, message: str):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = email_sender
    msg['To'] = email_receiver

    # Substitua os espaços reservados pelas informações do seu servidor SMTP
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_username = "geraldo.pereira@sempreceub.com"
    smtp_password = "30125047GGdf"


    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(msg['From'], msg['To'], msg.as_string())


@app.get("/")
async def root():
    return {"message": "API CEUBLIVRE-WISHLIST. Veja a documentação: /docs"}
