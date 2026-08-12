from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel
import os

# 1. 创建FastAPI实例
app = FastAPI(
    title="售后维保SaaS系统API",
    description="工业设备售后维保管理系统后端接口文档",
    version="1.0.0"
)

# 允许跨域（线上前端和后端域名不同需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. 数据库配置：本地用SQLite，线上自动用Render的PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./maintenance.db")
# 兼容不同平台的数据库连接串格式，使用纯Python的pg8000驱动
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)

connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 3. 定义5张核心数据表模型
class User(Base):
    """用户表：管理员/工程师"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, comment="登录账号")
    password = Column(String(100), comment="登录密码")
    name = Column(String(50), comment="姓名")
    role = Column(String(20), default="工程师", comment="角色：管理员/工程师")

class Customer(Base):
    """客户表"""
    __tablename__ = "customers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), comment="客户名称")
    contact_person = Column(String(50), comment="联系人")
    phone = Column(String(20), comment="联系电话")
    address = Column(String(255), comment="地址")

class Device(Base):
    """设备表"""
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    device_no = Column(String(50), unique=True, index=True, comment="设备编号")
    model = Column(String(100), comment="设备型号")
    customer_id = Column(Integer, ForeignKey("customers.id"), comment="所属客户ID")
    install_date = Column(DateTime, comment="安装时间")
    warranty_expire = Column(DateTime, comment="保修到期时间")

class WorkOrder(Base):
    """工单表（核心表）"""
    __tablename__ = "work_orders"
    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(50), unique=True, index=True, comment="工单编号")
    customer_id = Column(Integer, ForeignKey("customers.id"), comment="客户ID")
    device_id = Column(Integer, ForeignKey("devices.id"), comment="故障设备ID")
    fault_type = Column(String(50), comment="故障类型：电气故障/机械故障/管路故障/定期保养")
    priority = Column(String(20), default="中", comment="优先级：低/中/高/紧急")
    status = Column(String(20), default="待派单", comment="工单状态：待派单/待接单/已接单/维修中/待验收/已完成/已取消")
    description = Column(Text, comment="故障描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    engineer_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="负责工程师ID，派单后有值")

# 4. 启动时自动创建所有数据表
Base.metadata.create_all(bind=engine)

# 5. 数据库依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 6. 请求参数模型（Pydantic自动校验参数）
class OrderCreate(BaseModel):
    customer_id: int
    device_id: int
    fault_type: str
    priority: str = "中"
    description: str

class OrderDispatch(BaseModel):
    engineer_id: int

class OrderStatusUpdate(BaseModel):
    status: str

# 7. 合法状态流转规则（核心业务逻辑，严格按PRD来）
STATUS_TRANSITIONS = {
    "待派单": ["待接单", "已取消"],
    "待接单": ["已接单", "已取消"],
    "已接单": ["维修中", "已取消"],
    "维修中": ["待验收", "已取消"],
    "待验收": ["已完成", "维修中"],  # 验收不通过可以打回维修中
    "已完成": [],
    "已取消": []
}

# 8. 基础接口
@app.get("/", summary="服务健康检查")
def root():
    return {"message": "售后维保SaaS后端服务已启动", "status": "running", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# 9. 基础下拉数据接口（给前端新建工单/派单用）
@app.get("/api/engineers", summary="获取工程师列表")
def get_engineers(db: Session = Depends(get_db)):
    engineers = db.query(User).filter(User.role == "工程师").all()
    return {"code": 200, "data": [{"id": e.id, "name": e.name} for e in engineers]}

@app.get("/api/customers", summary="获取客户列表")
def get_customers(db: Session = Depends(get_db)):
    customers = db.query(Customer).all()
    return {"code": 200, "data": [{"id": c.id, "name": c.name} for c in customers]}

@app.get("/api/devices", summary="获取设备列表（可按客户筛选）")
def get_devices(customer_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Device)
    if customer_id:
        query = query.filter(Device.customer_id == customer_id)
    devices = query.all()
    return {"code": 200, "data": [{"id": d.id, "device_no": d.device_no, "model": d.model, "customer_id": d.customer_id} for d in devices]}

# 10. 工单核心接口
@app.get("/api/orders", summary="获取工单列表（支持状态筛选、分页）")
def get_orders(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(WorkOrder)
    if status:
        query = query.filter(WorkOrder.status == status)
    total = query.count()
    orders = query.order_by(WorkOrder.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
    
    # 关联查询客户、设备、工程师名称
    result = []
    for order in orders:
        customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
        device = db.query(Device).filter(Device.id == order.device_id).first()
        engineer = db.query(User).filter(User.id == order.engineer_id).first() if order.engineer_id else None
        result.append({
            "id": order.id,
            "order_no": order.order_no,
            "customer_name": customer.name if customer else "",
            "device_no": device.device_no if device else "",
            "device_model": device.model if device else "",
            "fault_type": order.fault_type,
            "priority": order.priority,
            "status": order.status,
            "created_at": order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "",
            "engineer_name": engineer.name if engineer else ""
        })
    return {"code": 200, "total": total, "data": result}

@app.post("/api/orders", summary="新建工单")
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    # 自动生成工单编号：GD+年月日+3位序号
    today_str = date.today().strftime("%Y%m%d")
    today_count = db.query(WorkOrder).filter(func.date(WorkOrder.created_at) == date.today()).count()
    order_no = f"GD{today_str}{today_count + 1:03d}"
    
    db_order = WorkOrder(
        order_no=order_no,
        customer_id=order.customer_id,
        device_id=order.device_id,
        fault_type=order.fault_type,
        priority=order.priority,
        description=order.description,
        status="待派单"
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return {"code": 200, "message": "工单创建成功", "data": {"id": db_order.id, "order_no": db_order.order_no}}

@app.get("/api/orders/{order_id}", summary="获取工单详情")
def get_order_detail(order_id: int, db: Session = Depends(get_db)):
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
    device = db.query(Device).filter(Device.id == order.device_id).first()
    engineer = db.query(User).filter(User.id == order.engineer_id).first() if order.engineer_id else None
    
    return {
        "code": 200,
        "data": {
            "id": order.id,
            "order_no": order.order_no,
            "customer_id": order.customer_id,
            "customer_name": customer.name if customer else "",
            "contact_person": customer.contact_person if customer else "",
            "customer_phone": customer.phone if customer else "",
            "customer_address": customer.address if customer else "",
            "device_id": order.device_id,
            "device_no": device.device_no if device else "",
            "device_model": device.model if device else "",
            "fault_type": order.fault_type,
            "priority": order.priority,
            "status": order.status,
            "description": order.description,
            "created_at": order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "",
            "engineer_id": order.engineer_id,
            "engineer_name": engineer.name if engineer else ""
        }
    }

@app.post("/api/orders/{order_id}/dispatch", summary="派单（分配工程师）")
def dispatch_order(order_id: int, dispatch: OrderDispatch, db: Session = Depends(get_db)):
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="工单不存在")
    if order.status != "待派单":
        raise HTTPException(status_code=400, detail="只有待派单状态的工单才能派单")
    
    engineer = db.query(User).filter(User.id == dispatch.engineer_id, User.role == "工程师").first()
    if not engineer:
        raise HTTPException(status_code=400, detail="所选工程师不存在")
    
    order.engineer_id = dispatch.engineer_id
    order.status = "待接单"
    db.commit()
    return {"code": 200, "message": "派单成功"}

@app.put("/api/orders/{order_id}/status", summary="更新工单状态（自动校验流转规则）")
def update_order_status(order_id: int, status_update: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="工单不存在")
    
    target_status = status_update.status
    # 校验状态是否合法
    if target_status not in STATUS_TRANSITIONS:
        raise HTTPException(status_code=400, detail=f"非法状态：{target_status}")
    # 校验流转是否允许
    if target_status not in STATUS_TRANSITIONS[order.status]:
        raise HTTPException(status_code=400, detail=f"不允许从【{order.status}】变更为【{target_status}】")
    
    order.status = target_status
    db.commit()
    return {"code": 200, "message": f"状态已更新为【{target_status}】"}

# 11. 客户管理CRUD
class CustomerCreate(BaseModel):
    name: str
    contact_person: str
    phone: str
    address: str

@app.get("/api/customers/list", summary="客户管理列表（分页）")
def get_customer_list(page: int = 1, page_size: int = 10, keyword: str = "", db: Session = Depends(get_db)):
    query = db.query(Customer)
    if keyword:
        query = query.filter(Customer.name.like(f"%{keyword}%"))
    total = query.count()
    customers = query.offset((page-1)*page_size).limit(page_size).all()
    result = []
    for c in customers:
        device_count = db.query(Device).filter(Device.customer_id == c.id).count()
        result.append({
            "id": c.id, "name": c.name, "contact_person": c.contact_person,
            "phone": c.phone, "address": c.address, "device_count": device_count
        })
    return {"code": 200, "total": total, "data": result}

@app.post("/api/customers", summary="新增客户")
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    db_customer = Customer(**customer.dict())
    db.add(db_customer)
    db.commit()
    return {"code": 200, "message": "新增成功"}

@app.put("/api/customers/{customer_id}", summary="编辑客户")
def update_customer(customer_id: int, customer: CustomerCreate, db: Session = Depends(get_db)):
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="客户不存在")
    for k, v in customer.dict().items():
        setattr(db_customer, k, v)
    db.commit()
    return {"code": 200, "message": "修改成功"}

@app.delete("/api/customers/{customer_id}", summary="删除客户")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    db.query(Customer).filter(Customer.id == customer_id).delete()
    db.commit()
    return {"code": 200, "message": "删除成功"}

# 12. 设备管理CRUD
class DeviceCreate(BaseModel):
    device_no: str
    model: str
    customer_id: int
    install_date: Optional[str] = None
    warranty_expire: Optional[str] = None

@app.get("/api/devices/list", summary="设备管理列表（分页）")
def get_device_list(page: int = 1, page_size: int = 10, keyword: str = "", db: Session = Depends(get_db)):
    query = db.query(Device)
    if keyword:
        query = query.filter(Device.device_no.like(f"%{keyword}%") | Device.model.like(f"%{keyword}%"))
    total = query.count()
    devices = query.offset((page-1)*page_size).limit(page_size).all()
    result = []
    for d in devices:
        customer = db.query(Customer).filter(Customer.id == d.customer_id).first()
        result.append({
            "id": d.id, "device_no": d.device_no, "model": d.model,
            "customer_id": d.customer_id, "customer_name": customer.name if customer else "",
            "install_date": d.install_date.strftime("%Y-%m-%d") if d.install_date else "",
            "warranty_expire": d.warranty_expire.strftime("%Y-%m-%d") if d.warranty_expire else ""
        })
    return {"code": 200, "total": total, "data": result}

@app.post("/api/devices", summary="新增设备")
def create_device(device: DeviceCreate, db: Session = Depends(get_db)):
    install_date = datetime.strptime(device.install_date, "%Y-%m-%d") if device.install_date else None
    warranty_expire = datetime.strptime(device.warranty_expire, "%Y-%m-%d") if device.warranty_expire else None
    db_device = Device(
        device_no=device.device_no, model=device.model, customer_id=device.customer_id,
        install_date=install_date, warranty_expire=warranty_expire
    )
    db.add(db_device)
    db.commit()
    return {"code": 200, "message": "新增成功"}

@app.put("/api/devices/{device_id}", summary="编辑设备")
def update_device(device_id: int, device: DeviceCreate, db: Session = Depends(get_db)):
    db_device = db.query(Device).filter(Device.id == device_id).first()
    if not db_device:
        raise HTTPException(status_code=404, detail="设备不存在")
    db_device.device_no = device.device_no
    db_device.model = device.model
    db_device.customer_id = device.customer_id
    if device.install_date:
        db_device.install_date = datetime.strptime(device.install_date, "%Y-%m-%d")
    if device.warranty_expire:
        db_device.warranty_expire = datetime.strptime(device.warranty_expire, "%Y-%m-%d")
    db.commit()
    return {"code": 200, "message": "修改成功"}

@app.delete("/api/devices/{device_id}", summary="删除设备")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    db.query(Device).filter(Device.id == device_id).delete()
    db.commit()
    return {"code": 200, "message": "删除成功"}

# 13. 数据看板统计
@app.get("/api/dashboard/stats", summary="看板统计数据")
def get_dashboard_stats(db: Session = Depends(get_db)):
    total = db.query(WorkOrder).count()
    pending_dispatch = db.query(WorkOrder).filter(WorkOrder.status == "待派单").count()
    processing = db.query(WorkOrder).filter(WorkOrder.status.in_(["待接单", "已接单", "维修中", "待验收"])).count()
    finished = db.query(WorkOrder).filter(WorkOrder.status == "已完成").count()
    
    # 各状态工单数量
    status_stats = []
    for status in ["待派单", "待接单", "维修中", "待验收", "已完成", "已取消"]:
        count = db.query(WorkOrder).filter(WorkOrder.status == status).count()
        status_stats.append({"name": status, "value": count})
    
    # 待办工单（待派单+待接单）
    todo_orders = db.query(WorkOrder).filter(WorkOrder.status.in_(["待派单", "待接单"])).order_by(WorkOrder.created_at.desc()).limit(5).all()
    todo_list = []
    for o in todo_orders:
        customer = db.query(Customer).filter(Customer.id == o.customer_id).first()
        todo_list.append({
            "id": o.id, "order_no": o.order_no,
            "customer_name": customer.name if customer else "",
            "status": o.status, "created_at": o.created_at.strftime("%m-%d %H:%M")
        })
    
    return {
        "code": 200,
        "overview": {
            "total": total, "pending_dispatch": pending_dispatch,
            "processing": processing, "finished": finished
        },
        "status_stats": status_stats,
        "todo_list": todo_list
    }

# 14. 一键生成测试数据（方便测试，不用自己一个个填）
@app.post("/api/init-test-data", summary="一键生成测试数据（工程师/客户/设备/测试工单）")
def init_test_data(db: Session = Depends(get_db)):
    # 先清空旧数据
    db.query(WorkOrder).delete()
    db.query(Device).delete()
    db.query(Customer).delete()
    db.query(User).filter(User.role == "工程师").delete()
    db.commit()
    
    # 添加工程师
    engineers = [
        User(username="zhang", password="123456", name="张师傅", role="工程师"),
        User(username="li", password="123456", name="李师傅", role="工程师"),
        User(username="wang", password="123456", name="王师傅", role="工程师"),
    ]
    db.add_all(engineers)
    db.flush()
    
    # 添加客户
    customers = [
        Customer(name="XX机械有限公司", contact_person="王主任", phone="138****5678", address="XX市XX区工业园12号"),
        Customer(name="XX电子科技有限公司", contact_person="李经理", phone="139****1234", address="XX市XX区开发区8号"),
        Customer(name="XX食品加工厂", contact_person="张厂长", phone="137****9876", address="XX市XX区食品工业园3号"),
    ]
    db.add_all(customers)
    db.flush()
    
    # 添加设备
    devices = [
        Device(device_no="SB202603001", model="CK6140数控车床", customer_id=customers[0].id, install_date=datetime(2026,3,15), warranty_expire=datetime(2027,3,14)),
        Device(device_no="SB202602015", model="VMC850加工中心", customer_id=customers[1].id, install_date=datetime(2026,2,20), warranty_expire=datetime(2027,2,19)),
        Device(device_no="SB202601008", model="LD-100激光切割机", customer_id=customers[2].id, install_date=datetime(2026,1,10), warranty_expire=datetime(2027,1,9)),
    ]
    db.add_all(devices)
    db.flush()
    
    # 添加测试工单
    orders = [
        WorkOrder(order_no="GD20260807001", customer_id=customers[0].id, device_id=devices[0].id, fault_type="电气故障", priority="高", status="待派单", description="设备开机后无法启动，控制面板无显示，疑似电源模块故障"),
        WorkOrder(order_no="GD20260807002", customer_id=customers[1].id, device_id=devices[1].id, fault_type="机械故障", priority="中", status="待派单", description="设备运行时主轴有异响，振动较大"),
        WorkOrder(order_no="GD20260806008", customer_id=customers[2].id, device_id=devices[2].id, fault_type="定期保养", priority="低", status="待接单", description="季度定期保养，更换润滑油和滤芯", engineer_id=engineers[0].id),
        WorkOrder(order_no="GD20260806007", customer_id=customers[0].id, device_id=devices[0].id, fault_type="管路故障", priority="高", status="维修中", description="液压管路漏油，压力不足", engineer_id=engineers[1].id),
        WorkOrder(order_no="GD20260805012", customer_id=customers[1].id, device_id=devices[1].id, fault_type="电气故障", priority="中", status="待验收", description="伺服驱动器报警，已更换配件", engineer_id=engineers[0].id),
        WorkOrder(order_no="GD20260804009", customer_id=customers[2].id, device_id=devices[2].id, fault_type="电气故障", priority="中", status="已完成", description="电源开关损坏，已更换", engineer_id=engineers[2].id),
        WorkOrder(order_no="GD20260803005", customer_id=customers[0].id, device_id=devices[0].id, fault_type="机械故障", priority="低", status="已完成", description="导轨润滑保养", engineer_id=engineers[0].id),
    ]
    db.add_all(orders)
    db.commit()
    
    return {"code": 200, "message": "测试数据生成成功：3个工程师、3个客户、3台设备、7条测试工单"}
