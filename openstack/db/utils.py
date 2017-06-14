# coding: utf-8
__author__ = 'cshuo'


from .entity import Vm
from .entity import ShareStatus
from .entity import InvolvedHost
from .entity import Rules
import time

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


sqlURL = 'mysql://dra:cshuo@IP:PORT/machineDB'
engine = create_engine(sqlURL)

DBSession = sessionmaker(bind=engine)


def creat_vm_table():
    metaData= MetaData()
    vmTable = Table('vm', metaData,
            Column('ids', String(40), primary_key=True),
            Column('name', String(32)),
            Column('vm_type', String(32)),
            )
    metaData.create_all(engine)


def create_status_table():
    metaData= MetaData()
    statusTable = Table('status', metaData,
                        Column('name', String(40), primary_key=True),
                        Column('timestamp', String(40)),
                        )
    metaData.create_all(engine)


def create_involved_table():
    metaData= MetaData()
    involvedTable = Table('involved', metaData,
                        Column('name', String(40), primary_key=True),
                        )
    metaData.create_all(engine)

def create_rules_table():
    metaData = MetaData()
    rulesTable = Table('rules', metaData,
                        Column('name', String(40), primary_key=True),
                        Column('app_type', String(40)),
                        Column('content', Text()),
                        )
    metaData.create_all(engine)


class RuleDb(object):
    def __init__(self):
        self.engine = engine

    @staticmethod
    def add_rule(name, app_type, content):
        session = DBSession()
        new_rule = Rules(name=name, app_type=app_type, content=content)
        try:
            session.add(new_rule)
            session.commit()
        except:
            session.close()
            return False
        session.close()
        return True

    @staticmethod
    def rm_rule(name):
        session = DBSession()
        try:
            rule = session.query(Rules).filter(Rules.name==name).one()
        except:
            session.close()
            return False
        session.delete(rule)
        session.commit()
        session.close()
        return True

    @staticmethod
    def query_rule(name):
        session = DBSession()
        try:
            rule = session.query(Rules).filter(Rules.name==name).one()
        except:
            session.close()
            return None
        session.close()
        return {'name': rule.name, 'app_type':rule.app_type, 'conten': rule.content}


    @staticmethod
    def list_rules():
        session = DBSession()
        try:
            rules = session.query(Rules).all()
        except:
            session.close()
            return None
        session.close()
        ret_info = []
        for r in rules:
            ret_info.append({'name': r.name, 'app_type':r.app_type, 'content':r.content})
        return ret_info


class DismissStatus(object):
    def __int__(self):
        self.engine = engine

    @staticmethod
    def add_involved(name):
        session = DBSession()
        new_invol = InvolvedHost(name=name)
        try:
            session.add(new_invol)
            session.commit()
        except:
            session.close()
            return False
        session.close()
        return True

    @staticmethod
    def get_involved():
        sessoin = DBSession()
        involed_hs = sessoin.query(InvolvedHost).all()
        ret_hs = []
        for h in involed_hs:
            ret_hs.append(h.name)
        return ret_hs

    @staticmethod
    def clear_involved():
        session = DBSession()
        for h in DismissStatus.get_involved():
            try:
                involved_h = session.query(InvolvedHost).filter(InvolvedHost.name == h).one()
            except:
                pass
            session.delete(involved_h)
        session.commit()
        session.close()

    @staticmethod
    def add_dismiss(name, timestamp):
        session = DBSession()
        new_dismiss = ShareStatus(name=name, timestamp=timestamp)
        try:
            session.add(new_dismiss)
            session.commit()
        except:
            session.close()
            return False
        session.close()
        return True

    @staticmethod
    def rm_dismiss(name):
        session = DBSession()
        try:
            dismiss = session.query(ShareStatus).filter(ShareStatus.name==name).one()
        except:
            session.close()
            return False
        session.delete(dismiss)
        session.commit()
        session.close()
        return True

    @staticmethod
    def query_num():
        session = DBSession()
        dismes = session.query(ShareStatus).all()
        return len(dismes)


class DbUtil(object):
    def __init__(self):
        self.engine = engine

    def add_vm(self, ids, name, vm_type):
        session = DBSession()
        new_vm = Vm(ids=ids, name=name, vm_type=vm_type)
        try:
            session.add(new_vm)
            session.commit()
        except:
            session.close()
            return False
        session.close()
        return True

    def rm_vm(self, vm_ids):
        """
        return True for delete vm successfully, or return False
        """
        session = DBSession()
        try:
            vm_inst = session.query(Vm).filter(Vm.ids==vm_ids).one()
        except:
            session.close()
            return False
        session.delete(vm_inst)
        session.commit()
        session.close()
        return True

    def query_vm(self, vm_ids):
        """
        return dict of vm info, None for None
        """
        session = DBSession()
        try:
            vm_inst = session.query(Vm).filter(Vm.ids == vm_ids).one()
        except:
            session.close()
            return None
        vm_info = {'ids': vm_inst.ids, 'name': vm_inst.name, 'type': vm_inst.vm_type}
        session.close()
        return vm_info

    def list_all(self):
        """
        """
        session = DBSession()
        vms = session.query(Vm).all()
        session.close()
        return vms


if __name__ == '__main__':
    creat_vm_table()
    create_involved_table()
    create_status_table()
    create_rules_table()

    db = DbUtil()
    # print db.list_all()
    # db.rm_vm('584513aa-20ee-46ce-8229-4517104c211a')
    # for i in db.list_all():
    #     print i.name, i.ids, i.vm_type
    # # Vm.__table__.drop(engine)
    """
    if db.add_vm('1212-1212-2121', 'test1', 'normal'):
        print "add ok"
    """
    # DismissStatus.rm_dismiss('compute1')
    # DismissStatus.rm_dismiss('compute2')
    # while 1:
    #     print DismissStatus.query_num()
    #     time.sleep(0.5)
    # DismissStatus.add_involved('compute1')
    # DismissStatus.add_involved('compute2')
    # print DismissStatus.get_involved()
    # DismissStatus.clear_involved()
    # print DismissStatus.query_num()
    # print db.query_vm('c4d73b6b-4d28-4cde-a8a8-b31613162da8')
    RuleDb.add_rule('matlab', 'matlab_slave', """(defrule underload_valid_check
        (declare (salience 100))
        ?dismiss &lt;- (dismiss (host ?host))
        =>
        (if (= (python-call hostInvolved ?host) 1)
            then
            (python-call print_log "The host is involved in early round processing....")
            (retract ?dismiss)
            (python-call clearDismissCache ?host)
            else
            (python-call print_log "continue deal with the underload...")
        ))
        """)
    rules = RuleDb.list_rules()
    print rules
    print RuleDb.query_rule('matlabasdf')
    a = RuleDb.rm_rule('asdf')
    print a
    # RuleDb.rm_rule('matlab')
    # print RuleDb.list_rules()
