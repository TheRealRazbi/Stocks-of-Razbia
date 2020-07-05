from database import Company, Session, User
from commands import group, Group

registry = {}


class DummyCtx:
    def __init__(self):
        self.session = Session()
        self.user: User = self.session.query(User).first()


stock = group(name="stock", registry=registry)


@stock.command()
def buy(ctx: DummyCtx, company: Company, amount: int):
    print(f"{ctx.user.name} buying {amount} stocks from {company.full_name}")


@stock.command()
def sell(ctx: DummyCtx, company: Company, amount: int):
    print(f"{ctx.user.name} selling {amount} stocks from {company.full_name}")


def exec_cmd(args):
    args = args.split(" ")
    ctx = DummyCtx()
    registry[args[0]](ctx, *args[1:])


def test_1():
    raw_args = "stock buy RZBI 10"
    exec_cmd(raw_args)
