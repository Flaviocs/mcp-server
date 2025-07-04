import os   
import logging
import json
from pathlib import Path
import mysql.connector
from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import httpx
import time

#Carregando variaveis de ambiente do arquivo .env
dotenv_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=dotenv_path)


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mcp.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("mcp_server")
class TimedCache:
    """Cache com tempo de expiração (Time-To-Live)"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        self.cache[key] = (value, time.time())


class BuscarColetivosTool:
    """Ferramenta para buscar coletivos/turmas no sistema RAE"""
    
    BASE_URL = os.getenv("RAE_API_URL", "https://raeconsultascoletivo.sp.sebrae.com.br/api/BuscarColetivos")
    HEADERS = {
        "accept": "text/plain",
        "hash": os.getenv("RAE_API_HASH")
    }
    
    TIMEOUT = float(os.getenv("RAE_API_TIMEOUT", "10.0"))
    MAX_ITEMS_PER_PAGE = int(os.getenv("RAE_MAX_ITEMS", "100"))
    CACHE_TTL = int(os.getenv("RAE_CACHE_TTL", "300"))



#Conectando ao banco de dados MySQL
def conectar_banco_de_dados():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            charset='utf8mb4', 
            collation='utf8mb4_general_ci'
        )
        if conn.is_connected():
            logging.info("Conectado ao banco de dados MySQL")
            return conn
        else:
            logging.error("Não foi possível conectar ao banco de dados MySQL")
            return None
        
    except mysql.connector.Error as e:
        logging.error(f"Erro ao conectar ao banco de dados: {e}")
        return None

def ver_cursos_db() -> dict:
    """
    Conectar com o banco de dados e consultar a tabela de cursos
    """
    lista = []
    try:
        conn = conectar_banco_de_dados()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cursos")
            cursos = cursor.fetchall()

            for row in cursos:
                ID, Curso, Descr_Curso, Data_Realizacao = row
                lista.append({"ID": ID, "Curso": Curso, "Descr_Curso": Descr_Curso, "Data_Realizacao": Data_Realizacao})               

            return lista
        else:
            logging.error("Não foi possível conectar ao banco de dados MySQL")
            return None
    except mysql.connector.Error as e:
        logging.error(f"Erro ao conectar ao banco de dados: {e}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()
            print("Conexão MySQL fechada.")


turmas_cache = TimedCache(ttl_seconds=BuscarColetivosTool.CACHE_TTL)
# Criando o servidor MCP
mcp = FastMCP("Flavio MCP")

@mcp.resource("config://app")
def get_greeting() -> str:
    return f"Olá, eu sou o Flavio MCP"

#Adicionando o endpoint /mcp/tools
@mcp.tool()
def lista_nomes() -> dict:
    """
    Consulta a lista de nomes
    
    Returns:
        dict: Dicionário contendo a lista de nomes
    """
    nomes = ["Flavio", "João", "Maria", "Pedro", "Ana", "Carlos", "Lucas", "Rafael", "Bruno", "Diego"]

    return dict(list=nomes)


@mcp.tool()
def ver_xxxxxx() -> list:
    """
    Consulta a lista de xxxxxxx
    
    Returns:
        dict: Dicionário contendo a lista de xxxxxx
    """
    cursos = ver_cursos_db()
    return list(cursos)  #Retorna o dicionário com a lista de cursos


@mcp.tool()
async def ver_turmas(codProduto: int, idSituacaoColetivo: int = 4, pagina: int = 0, quantidadePorPagina: int = 50) ->list:
    """
    Consultar de turmas / eventos abertos no Sebrae São Paulo para um determinado produto ou serviço ou curso ou palestras

     Args:
        Codigo produto: código / id do produto ou serviço do portfólio.        

    Returns:
        list: lista contendo os cursos que estão abertos para um determinado produto
    """
    #if pagina < 0:
        #logger.error(f"Parâmetro inválido: pagina={pagina}")
        #return {"sucesso": False, "erro": "A página não pode ser negativa"}
    
       # if quantidade_por_pagina <= 0 or quantidade_por_pagina > BuscarColetivosTool.MAX_ITEMS_PER_PAGE:
       #     logger.error(f"Parâmetro inválido: quantidade_por_pagina={quantidade_por_pagina}")
       #     return {
       #         "sucesso": False,
       #         "erro": f"Quantidade por página deve estar entre 1 e {BuscarColetivosTool.MAX_ITEMS_PER_PAGE}"
       #     }
        
    url = f"{BuscarColetivosTool.BASE_URL}?idProduto={codProduto}&pagina={pagina}&quantidadePorPagina={quantidadePorPagina}&idSituacaoColetivo={idSituacaoColetivo}"
    cache_key = f"{codProduto}_{idSituacaoColetivo}_{pagina}_{quantidadePorPagina}"
    
    cached_result = turmas_cache.get(cache_key)
    if cached_result:
        logger.info(f"Usando resultado em cache para: {cache_key}")
        return {"sucesso": True, "dados": cached_result}
    
    logger.info(f"Consultando turmas: idProduto={codProduto}, idSituacaoColetivo={idSituacaoColetivo}, pagina={pagina}")
    
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                url,
                headers=BuscarColetivosTool.HEADERS,
                timeout=BuscarColetivosTool.TIMEOUT
            )
            response.raise_for_status()
            result = response.json()
            coletivos = result.get("coletivos", "[]")
            print("  XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
            print(coletivos)
            print("  XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
            if not coletivos:
                logger.warning("Nenunha turma encontratada para esse pprduto")
                return {"sucesso": False, "erro": f"Nenhuma turma aberta encontrada para o produto {codProduto}."}

            turmas_formatadas = []
            for c in coletivos:
                turma = {
                    "idColetivo": c.get("idColetivo"),
                    "idProduto": c.get("idProduto"),
                    "dataInicio": c.get("dataInicio"),
                    "dataFim": c.get("dataFim"),
                    "situacao": c.get("situacao"),
                    "pertenceAKit": c.get("pertenceAKit")
                }
                turmas_formatadas.append(turma)

            #if not isinstance(result, dict):
            #    logger.warning("Resposta inesperada da API.")
            #    return {"sucesso": False, "erro": "Resposta inesperada da API"}

            turmas_cache.set(cache_key, turmas_formatadas)
            return {"sucesso": True, "dados": turmas_formatadas}

    except httpx.HTTPStatusError as e:
        logger.error(f"Erro HTTP {e.response.status_code}: {e.response.text}")
        return {"sucesso": False, "erro": f"xxxxxxxxxxxxxxErro na requisição: {e.response.status_code}","mensagem": e.response.text}
    except httpx.RequestError as e:
        logger.error(f"Erro de conexão: {str(e)}")
        return {"sucesso": False, "erro": f"zzzzzzzzzzzzzzFalha ao conectar: {str(e)}"}
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}", exc_info=True)
        return {"sucesso": False, "erro": f"wwwwwwwwwwwwwwwwwErro inesperado: {str(e)}"}



if __name__ == "__main__":
    print("Iniciando o servidor MCP")

    try:
        mcp.run(transport="sse")
    except Exception as e:
        logging.warning(f"Erro ao iniciar o servidor MCP: {e}")
        exit(1)

    print("Servidor MCP iniciado")

