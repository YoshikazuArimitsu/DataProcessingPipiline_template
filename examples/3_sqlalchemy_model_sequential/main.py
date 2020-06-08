from repository.sqlalchemy_repository import SqlAlchemyRepository
from data.sqlalchemy_model_data import SqlAlchemyModelData
import os
from sqlalchemy import create_engine
from logging import getLogger, basicConfig, DEBUG
from logging.config import dictConfig
from graph.graph import Graph
from pathlib import Path
from task.task import Task
from dataset.dataset import DataSet
from data.dataframe_data import DataFrameData
from data.raw_data import RawData
from repository.localfile_repository import LocalFileRepository
from repository.repository import Repository
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Boolean, Column, DateTime, Enum, Float, ForeignKey,
                        Integer, String, Text, event)

logger = getLogger(__name__)

Base = declarative_base()


class Titanic(Base):
    __tablename__ = 'titanic'

    PassengerId = Column(Integer, primary_key=True)
    Survived = Column(Integer)
    Pclass = Column(Integer)
    Name = Column(String)
    Sex = Column(String)
    Age = Column(Integer)
    SibSp = Column(Integer)
    Parch = Column(Integer)
    Ticket = Column(String)
    Fare = Column(Float)
    Cabin = Column(String)
    Embarked = Column(String)


class SexToCode(Task):
    """性別をcodeに変換するTask
    """

    def main(self, ds):
        df = ds.get('titanic').to_dataframe()

        df["Sex"][df["Sex"] == "male"] = 0
        df["Sex"][df["Sex"] == "female"] = 1

        ds.get('titanic').update_dataframe(df)
        return ds


class EmbarkedToCode(Task):
    def main(self, ds):
        df = ds.get('titanic').to_dataframe()

        df["Embarked"] = df["Embarked"].fillna("S")
        df["Embarked"][df["Embarked"] == "S"] = 0
        df["Embarked"][df["Embarked"] == "C"] = 1
        df["Embarked"][df["Embarked"] == "Q"] = 2

        ds.get('titanic').update_dataframe(df)
        return ds


def prepare_db(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    repo = LocalFileRepository(
        Path(os.path.dirname(__file__)) / Path('../titanic.csv'))
    titanic_data = DataFrameData.load(repo)

    repo_s = SqlAlchemyRepository(engine)

    md = SqlAlchemyModelData(repo_s, Titanic)
    md.update_dataframe(titanic_data.content)
    md.save()


if __name__ == '__main__':
    basicConfig(level=DEBUG)

    # データセットの読み込み・DBの準備
    engine = create_engine('sqlite:///example.sqlite3', echo=True)
    prepare_db(engine)

    repo = SqlAlchemyRepository(engine)
    d = SqlAlchemyModelData(repo, Titanic)
    d.query()
    passenger_ids = [m.PassengerId for m in d.content]

    # データを一行ずつ SQLAlchemy のモデルに取り出し、処理して書き戻す例
    for passenger_id in passenger_ids:
        d.query(lambda x: x.filter(Titanic.PassengerId == passenger_id))

        ds = DataSet()
        ds.put('titanic', d)
        ds = SexToCode().main(ds)
        ds = EmbarkedToCode().main(ds)

        ds.save_all()
