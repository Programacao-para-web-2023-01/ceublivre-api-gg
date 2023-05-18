from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from deta import Deta
import smtplib
from email.mime.text import MIMEText

app = FastAPI()

deta = Deta('e05tW9KfFXAh_1X6VitLLEkY14CfB4eNXwHWStznACk91')
dbUsers = deta.Base("Users")  # Base temp. de usuários
dbProducts = deta.Base("Products")  # Base de produtos ativos temp.
dbWishlist = deta.Base("wishlists")  # base de wishlists(?)

drive = deta.Drive("Images")  # Drive de Imagens (ativos)
dbInactiveProducts = deta.Base("ProductDatabase")  # Base de produtos(Inativos)


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

@app.get("/wishlist/{id}")  # melhor implementavél quando disponibilizado autenticação
async def get_wishlist_by_id(id: str):
    check_u = dbUsers.get(id)  # verificação da existencia do usuário
    if not check_u:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    wishlist_items = dbWishlist.fetch(
        {"cod_user": id}).items  # verificação da existencia de wishlist do usuário e definido lista dos valores
    if not wishlist_items:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado na lista de desejos do usuário.")
    keys = [item["cod_product"] for item in wishlist_items]  # definido lista das chaves do produto
    # Consulta para obter os nomes dos produtos com base nas chaves
    products = []  # definir lista de dict vázio
    for key in keys:
        product = dbProducts.get(key)
        if product:  # definido formato das info do item
            product_info = {
                "nome": product["name"],
                "descrição": product["description"],
                "categoria": product["category"],
                "preço": product["price"]
            }
            products.append(product_info)  # adicionado os items como dicionario a lista

    if not products:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado na wishlist.")

    return products


@app.get("/wishlist")
async def get_user_wishlist(user_name: str):
    user = dbUsers.fetch({"name": user_name}).items  # verificação da existencia do usuário
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    wishlist_items = dbWishlist.fetch(
        {"cod_user": user[0]["key"]}).items  # verificação da existencia de wishlist do usuário
    if not wishlist_items:
        raise HTTPException(status_code=404, detail="Nenhum produto encontrado na lista de desejos do usuário.")

    product_keys = [item["cod_product"] for item in wishlist_items]

    # Consulta para obter os nomes dos produtos com base nas chaves
    products = []  # definir dicionario vázio
    for key in product_keys:
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


@app.post("/wishlist")
async def insert_product_wishlist(iduser: str, idproduct: str):
    check_p_key = dbProducts.get(idproduct)  # validação do produto na lista de produtos
    check_u_key = dbUsers.get(iduser)  # validação do usuário
    check_wishlist = dbWishlist.fetch({"cod_user": iduser,
                                       "cod_product": idproduct}).items  # validação do produto x usuário na lista -- fetch pois não foi passado valor dict
    # Verificação boleana dos checks
    if not check_p_key:
        raise HTTPException(status_code=404,
                            detail="Produto não encontrado. Verifique Codigo de produto e tente novamente.")
    if not check_u_key:
        raise HTTPException(status_code=404, detail="Falha ao identificar usuário. Verifique ID Login.")
    if check_wishlist:
        raise HTTPException(status_code=404, detail="Produto ja na lista de desejos do usuário.")

    new_item = {
        "cod_user": iduser,
        "cod_product": idproduct
    }
    dbWishlist.insert(new_item)  #

    #
    product = dbProducts.get(idproduct)
    if product:
        #
        current_price = product["price"]
        previous_price = get_previous_price(idproduct)
        if previous_price and current_price < previous_price:
            user_email = get_user_email(iduser)
            notification_message = f"O produto {product['nome']} está agora com preço reduzido!"
            send_notification(user_email, notification_message)

    return {"detail": "Adicionado a wishlist com sucesso."}


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


@app.post("/wishlistshare")
async def share_wishlist(email: str, wish_id: str):
    try:
        user = dbUsers.fetch({"mail": email}).items
        if not user:
            raise HTTPException(status_code=404, detail="Usuário com o e-mail fornecido não encontrado.")

        user_id = user[0]["key"]
        updated_wishlist = dbWishlist.update(wish_id, {"cod_user": user_id})
        if updated_wishlist is None:
            raise HTTPException(status_code=500, detail="Erro ao compartilhar lista de desejos.")

        return {"detail": f"Lista de desejos compartilhada com sucesso com o e-mail {email}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao compartilhar lista de desejos: {str(e)}")


def get_previous_price(product_id: str) -> float:
    product_history = dbInactiveProducts.fetch({"key": product_id}).items
    if product_history:
        # Assumindo que o histórico do produto é armazenado como uma lista de dicionários com campo "preço"
        prices = [item["price"] for item in product_history]
        previous_price = max(prices) if prices else None
        return previous_price
    else:
        return None


def send_notification(email: str, message: str):
    # Implemente a lógica para enviar a notificação por e-mail ou app
    # Para e-mail, você pode usar a biblioteca smtplib ou uma API de serviço de e-mail
    # Para notificações de aplicativos, use a biblioteca ou API específica para o serviço de notificação escolhido
    # Exemplo de código para envio de e-mail usando SMTP:
    smtp_host = 'your_smtp_host'
    smtp_port = 587
    smtp_user = 'your_smtp_username'
    smtp_password = 'your_smtp_password'
    sender_email = 'your_sender_email'
    subject = 'Notificação: Produto da lista de desejos à venda!'
    body = message
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = email
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(sender_email, email, msg.as_string())


def send_notification_disponibility(user_email: str, notification_message: str):
    # Verifique se o produto está disponível ou não
    is_available = check_product_availability()

    if is_available:
        # Enviar notificação por e-mail
        send_email_notification(user_email, notification_message)

        # Enviar notificação por meio de aplicativos
        send_app_notification(user_email, notification_message)
    else:
        # Produto não está disponível, não envie notificação
        pass

def check_product_availability() -> bool:
    # Retorna True se o produto estiver disponível, False caso contrário
    # Você pode substituir a lógica de exemplo abaixo por sua própria implementação
    # Lógica de exemplo: Supondo que a disponibilidade do produto esteja armazenada em um banco de dados ou API externa
    product_id = "your_product_id"
    product = dbProducts.get(product_id)
    if product and product.get("availability"):
        return True
    else:
        return False

