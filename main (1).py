
import os
from sqlmodel import SQLModel, create_engine, Session
from typing import Generator, Optional
from contextlib import contextmanager
from fastapi import Depends, FastAPI, HTTPException, status
from sqlmodel import select
from datetime import datetime, date

# Define the DATABASE_URL from environment variables or use a default for local development
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    # Default to a local SQLite database for development if DATABASE_URL is not set
    sqlite_file_name = "database.db"
    DATABASE_URL = f"sqlite:///{sqlite_file_name}"
    # For local SQLite, remove the file to ensure a clean start
    if os.path.exists(sqlite_file_name):
        os.remove(sqlite_file_name)


# Create the database engine using the DATABASE_URL
# Add connect_args={"check_same_thread": False} for SQLite compatibility, though a production DB won't need it
# but keeping it for local testing flexibility.
engine = create_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})

# Define models
class EmpresaSolicitante(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(index=True, description="Nome da empresa solicitante", min_length=1)
    cnpj: Optional[str] = Field(default=None, index=True, description="CNPJ da empresa solicitante", unique=True)
    responsavel: Optional[str] = Field(default=None, description="Nome do responsável na empresa")
    endereco: Optional[str] = Field(default=None, description="Endereço da empresa")
    telefone: Optional[str] = Field(default=None, description="Telefone da empresa")
    email: Optional[str] = Field(default=None, description="Email da empresa")

class Cliente(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(index=True)
    cnpj: Optional[str] = Field(default=None, unique=True)

class Contato(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    email: str = Field(unique=True)
    telefone: Optional[str] = Field(default=None)
    cliente_id: int = Field(foreign_key="cliente.id")

class Oportunidade(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    titulo: str
    valor_estimado: float
    status: str
    cliente_id: int = Field(foreign_key="cliente.id")

class Amostra(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    descricao: str
    data_solicitacao: Optional[date] = Field(default=None)
    status: str
    oportunidade_id: Optional[int] = Field(default=None, foreign_key="oportunidade.id")

class Orcamento(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="empresasolicitante.id")
    data_criacao: datetime = Field(default_factory=datetime.utcnow)
    validade_dias: Optional[int] = Field(default=None)
    prazo_entrega_dias: Optional[int] = Field(default=None)
    condicao_pagamento: Optional[str] = Field(default=None)
    ipi_percentual: Optional[float] = Field(default=None)
    observacoes: Optional[str] = Field(default=None)
    preco_bruto_total: float
    valor_ferramental_total: float
    valor_diluicao_ferramental_total: float
    valor_ipi_total: float
    preco_final_total: float

class OrcamentoItem(SQLModel, table=True):
    __table_args__ = {'extend_existing': True}
    id: Optional[int] = Field(default=None, primary_key=True)
    orcamento_id: int = Field(foreign_key="orcamento.id")
    referencia: str
    estilo_caixa: Optional[str] = Field(default=None)
    fechamento: Optional[str] = Field(default=None)
    numero_cores: Optional[int] = Field(default=None)
    medidas: Optional[str] = Field(default=None)
    qualidade: Optional[str] = Field(default=None)
    quantidade: int
    valor_ferramental: float
    valor_unitario: float
    valor_diluicao_ferramental_total: float
    valor_total: float
    ipi_percentual: Optional[float] = Field(default=None)

def create_db_and_tables():
    print("Creating database tables...")
    SQLModel.metadata.create_all(engine, checkfirst=True)
    print("Database tables created.")

# Dependency function to get a database session
def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session

# Define FastAPI app
app = FastAPI()

# Define endpoints
@app.post("/empresasolicitante/", response_model=EmpresaSolicitante)
def create_empresa_solicitante(empresa: EmpresaSolicitante, session: Session = Depends(get_session)):
    session.add(empresa)
    session.commit()
    session.refresh(empresa)
    return empresa

@app.get("/empresasolicitante/", response_model=list[EmpresaSolicitante])
def read_empresas_solicitantes(session: Session = Depends(get_session)):
    empresas = session.exec(select(EmpresaSolicitante)).all()
    return empresas

@app.get("/empresasolicitante/{empresa_id}", response_model=EmpresaSolicitante)
def read_empresa_solicitante(empresa_id: int, session: Session = Depends(get_session)):
    empresa = session.get(EmpresaSolicitante, empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="EmpresaSolicitante not found")
    return empresa

@app.put("/empresasolicitante/{empresa_id}", response_model=EmpresaSolicitante)
def update_empresa_solicitante(empresa_id: int, empresa: EmpresaSolicitante, session: Session = Depends(get_session)):
    db_empresa = session.get(EmpresaSolicitante, empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="EmpresaSolicitante not found")
    empresa_data = empresa.model_dump(exclude_unset=True)
    db_empresa.sqlmodel_update(empresa_data)
    session.add(db_empresa)
    session.commit()
    session.refresh(db_empresa)
    return db_empresa

@app.delete("/empresasolicitante/{empresa_id}")
def delete_empresa_solicitante(empresa_id: int, session: Session = Depends(get_session)):
    empresa = session.get(EmpresaSolicitante, empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="EmpresaSolicitante not found")
    session.delete(empresa)
    session.commit()
    return {"ok": True}

# Call create_db_and_tables() when the script is executed (e.g., by Uvicorn)
# This call is primarily for local development/testing within this script
# In a production deployment with Uvicorn, this function would typically be called
# as part of the application startup event.
# create_db_and_tables() # Commenting out for now to avoid errors in Colab environment if rerun

