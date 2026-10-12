import sqlalchemy as sa

from typing import List,Optional
from sqlalchemy import ForeignKey, ForeignKeyConstraint, Integer, String, Boolean, Text, select, TIMESTAMP,UniqueConstraint

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

from sqlalchemy import create_engine
import datetime, random

maxName = 30

class Base(DeclarativeBase):
    type_annotation_map = {
        datetime.datetime: TIMESTAMP(timezone=True)
        }


class Test(Base):
    __tablename__ = 'ecal_logger_tests'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(maxName))
    description: Mapped[str] = mapped_column(Text)

    run: Mapped["Entry"] = relationship(back_populates='test')

class Tower(Base):
    __tablename__ = 'towers'

    id_tower: Mapped[int] = mapped_column(primary_key = True)
    id_supermodule: Mapped[int] = mapped_column(ForeignKey('supermodules.id'))
    tower_in_sm: Mapped[int] = mapped_column()
    eta_sm: Mapped[int] = mapped_column()
    phi_sm: Mapped[int] = mapped_column()


class TowerMapping(Base):
    __tablename__ = 'sm_tower_mapping'
    tower_num_sm: Mapped[int] = mapped_column(primary_key=True) # 1..70
    tower_num_bcp: Mapped[int] = mapped_column(primary_key=True) # 0..11
    bcp_num: Mapped[int] = mapped_column(primary_key=True)

class Supermodule(Base):
    __tablename__ = "supermodules"

    id: Mapped[int] = mapped_column(primary_key = True)
    construction_id: Mapped[int] = mapped_column(primary_key = True)



class Entry(Base):
    __tablename__ = 'ecal_logger_entries'
    entry_id: Mapped[int] = mapped_column(primary_key=True, autoincrement='auto')
    test_id: Mapped[int] = mapped_column(ForeignKey('ecal_logger_tests.id'))
    run_number: Mapped[int] = mapped_column(ForeignKey('run_info.run_number'))
    func_name: Mapped[str] = mapped_column(String(maxName))
    result: Mapped[str] = mapped_column(Text)
    test_timestamp: Mapped[int]

    test: Mapped["Test"] = relationship(back_populates='run')
    
    run_info: Mapped["RunInfo"] = relationship(back_populates='entries')

# class Entry(Base):
#     __tablename__ = 'entries'
#     run_number: Mapped[int] = mapped_column(primary_key=True)
#     test_id: Mapped[int] = mapped_column(ForeignKey('tests.id'))
#     test_group_id: Mapped[int] = mapped_column(ForeignKey('test_groups.id'))
#     location: Mapped[str] = mapped_column(String(maxName))
#     updated: Mapped[datetime.datetime]
#     runs: Mapped[List["TestGroup"]] = relationship(back_populates='entries')

#     results: Mapped[List["Result"]] = relationship(back_populates='entry')

#     test: Mapped["Test"] = relationship(back_populates='run')

#     ForeignKeyConstraint(
#         ['test_id', 'test_group_id'], ["tests.id", "test_groups.id"]
#     )


class RunKey(Base):
    __tablename__ = 'run_keys'
    run_key_id: Mapped[int] = mapped_column(primary_key=True)
    tag: Mapped[str] = mapped_column(String(45))
    sequence: Mapped[str] = mapped_column(Text)
    id_daq_config: Mapped[int] = mapped_column()
    db_time: Mapped[datetime.datetime]
             
class RunInfo(Base):
    __tablename__ = 'run_info'

    run_number: Mapped[int] = mapped_column(primary_key=True)
    run_key_id: Mapped[int] = mapped_column(ForeignKey('run_keys.run_key_id'))
    id_daq_config: Mapped[int] = mapped_column()
    sm: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(45))
    starttime: Mapped[datetime.datetime]
    endtime: Mapped[datetime.datetime]
    entries: Mapped[List["Entry"]] = relationship(back_populates='run_info')


class BadMessage(Base):
    __tablename__ = 'ecal_logger_bad_messages'

    bad_message_id: Mapped[int] = mapped_column(primary_key=True, autoincrement='auto')
    received_at: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    topic: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    payload: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    exception: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


if __name__ == '__main__':
    dbPath = 'junk.db'
    liteEngine = create_engine('sqlite:///'+str(dbPath), echo=True, connect_args={'autocommit':True})
    print(Base.metadata.create_all(liteEngine))
