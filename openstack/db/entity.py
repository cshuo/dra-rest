# coding: utf-8
__author__ = 'cshuo'

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (
    create_engine, 
    Table, 
    Column, 
    Integer, 
    String,
    Text,
    MetaData, 
    ForeignKey
)

Base = declarative_base()


class Vm(Base):
    __tablename__ = 'vm'

    ids = Column(String(40), primary_key=True)
    name = Column(String(32))
    vm_type = Column(String(32))


class ShareStatus(Base):
    __tablename__ = 'status'
    name = Column(String(40), primary_key=True)
    timestamp = Column(String(40))


class InvolvedHost(Base):
    __tablename__ = 'involved'
    name = Column(String(40), primary_key=True)


class Rules(Base):
    __tablename__ = 'rules'
    name = Column(String(40), primary_key=True)
    app_type = Column(String(40))
    content = Column(Text())