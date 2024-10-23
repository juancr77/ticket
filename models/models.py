from sqlalchemy import Column, Integer, String, ForeignKey, Date, create_engine
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

# Configuración de SQLAlchemy
Base = declarative_base()

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        try:
            self.engine = create_engine('mysql+mysqlconnector://root@localhost/ticket', echo=True)
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
        except SQLAlchemyError as e:
            print(f"Error while connecting to the database: {e}")

    def get_session(self):
        return self.Session()

# ORM Models
class Asunto(Base):
    __tablename__ = 'asuntot'
    
    idAsunto = Column(Integer, primary_key=True, autoincrement=True)
    asuntoN = Column(String(100), nullable=False)

class Alumno(Base):
    __tablename__ = 'alumno'
    
    idAlumno = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100), nullable=False)
    primerApe = Column(String(100), nullable=False)
    segundoApe = Column(String(100), nullable=True)
    telefono = Column(String(100), nullable=False)
    correo = Column(String(100), nullable=False)
    idGrado = Column(Integer, ForeignKey('grado.idGrado'), nullable=False)
    idMunicipio = Column(Integer, ForeignKey('municipio.idMunicipio'), nullable=False)
    idAsunto = Column(Integer, ForeignKey('asuntot.idAsunto'), nullable=False)

    # Relación con Grado
    grado = relationship('Grado', back_populates='alumnos')

    # Relación con Municipio
    municipio = relationship('Municipio', back_populates='alumnos')

    # Relación con Asunto
    asunto = relationship('Asunto')

class Grado(Base):
    __tablename__ = 'grado'
    
    idGrado = Column(Integer, primary_key=True, autoincrement=True)
    gradoN = Column(String(100), nullable=False)

    # Relación con Alumno
    alumnos = relationship('Alumno', back_populates='grado')

class Municipio(Base):
    __tablename__ = 'municipio'
    
    idMunicipio = Column(Integer, primary_key=True, autoincrement=True)
    nombreN = Column(String(100), nullable=False)

    # Relación con Alumno
    alumnos = relationship('Alumno', back_populates='municipio')

class Ticket(Base):
    __tablename__ = 'tickett'
    
    idticket = Column(Integer, primary_key=True, autoincrement=True)
    ordTicket = Column(Integer, nullable=False)
    fecha = Column(Date, nullable=False)
    idestatus = Column(Integer, ForeignKey('estatus.idestatus'), nullable=False)
    idMunicipio = Column(Integer, ForeignKey('municipio.idMunicipio'), nullable=False)
    idAlumno = Column(Integer, ForeignKey('alumno.idAlumno'), nullable=False)
    idAsunto = Column(Integer, ForeignKey('asuntot.idAsunto'), nullable=False)

    # Relación con Estatus
    estatus = relationship('Estatus')

    # Relación con Municipio
    municipio = relationship('Municipio')

    # Relación con Alumno
    alumno = relationship('Alumno')

    # Relación con Asunto
    asunto = relationship('Asunto')

class Estatus(Base):
    __tablename__ = 'estatus'
    
    idestatus = Column(Integer, primary_key=True, autoincrement=True)
    detalle = Column(String(100), nullable=False)
