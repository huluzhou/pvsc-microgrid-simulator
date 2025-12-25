"""领域通用组件库使用示例"""

from datetime import datetime
from domain.common.entity import Entity, AggregateRoot
from domain.common.value_objects.base_value_object import ValueObject
from domain.common.value_objects.id_value_objects import EntityId, AggregateId
from domain.common.value_objects.parameter_value_objects import ParameterValue, UnitOfMeasure
from domain.common.value_objects.time_value_objects import TimeRange, Timestamp
from domain.common.events.domain_event import DomainEvent
from domain.common.events.event_bus import EventBus, EventHandler, InMemoryEventBus
from domain.common.specifications.base_specification import Specification
from domain.common.services.validation_service import ValidationService
from domain.common.services.specification_evaluator import SpecificationEvaluator
from domain.common.services.unit_conversion_service import UnitConversionService
from domain.common.services.time_service import TimeService
from domain.common.exceptions.base_exceptions import ValidationException, BusinessRuleViolationException

# 1. 实体和聚合根示例
class Product(Entity):
    def __init__(self, product_id: EntityId, name: str, price: float):
        super().__init__(product_id)
        self._name = name
        self._price = price
    
    @property
    def name(self):
        return self._name
    
    @property
    def price(self):
        return self._price

class Order(AggregateRoot):
    def __init__(self, order_id: AggregateId):
        super().__init__(order_id)
        self._products = []
        self._total = 0.0
    
    def add_product(self, product: Product, quantity: int):
        if quantity <= 0:
            raise BusinessRuleViolationException("Quantity must be positive")
        
        self._products.append((product, quantity))
        self._total += product.price * quantity
        self.update_timestamp()
        
        # 添加领域事件
        event = OrderProductAddedEvent(str(self.id), str(product.id), quantity)
        self.add_domain_event(event)

# 2. 领域事件示例
class OrderProductAddedEvent(DomainEvent):
    def __init__(self, order_id: str, product_id: str, quantity: int):
        super().__init__("OrderService", order_id)
        self._product_id = product_id
        self._quantity = quantity
    
    @property
    def product_id(self):
        return self._product_id
    
    @property
    def quantity(self):
        return self._quantity
    
    def event_type(self) -> str:
        return "OrderProductAdded"

# 3. 事件处理器示例
class OrderEventHandler(EventHandler):
    def handle(self, event: DomainEvent) -> None:
        if event.event_type() == "OrderProductAdded":
            print(f"处理订单商品添加事件: 订单ID={event.aggregate_id}, 商品ID={event.product_id}, 数量={event.quantity}")

# 4. 规格示例
class PriceGreaterThanSpecification(Specification[Product]):
    def __init__(self, min_price: float):
        self._min_price = min_price
    
    def is_satisfied_by(self, product: Product) -> bool:
        return product.price > self._min_price

class NameContainsSpecification(Specification[Product]):
    def __init__(self, keyword: str):
        self._keyword = keyword.lower()
    
    def is_satisfied_by(self, product: Product) -> bool:
        return self._keyword in product.name.lower()

# 5. 值对象示例
class Address(ValueObject):
    def __init__(self, street: str, city: str, zip_code: str):
        self._street = street
        self._city = city
        self._zip_code = zip_code
    
    def _get_eq_values(self):
        return [self._street, self._city, self._zip_code]

# 运行示例
if __name__ == "__main__":
    print("=== 领域通用组件库使用示例 ===\n")
    
    # 创建实体和聚合根
    product1 = Product(EntityId("p1"), "Laptop", 1500.0)
    product2 = Product(EntityId("p2"), "Smartphone", 800.0)
    product3 = Product(EntityId("p3"), "Tablet", 400.0)
    
    order = Order(AggregateId("order1"))
    
    # 添加商品到订单
    order.add_product(product1, 2)
    order.add_product(product2, 1)
    
    print(f"订单ID: {order.id}")
    print(f"订单创建时间: {order.created_at}")
    print(f"订单总金额: ${order._total}")
    
    # 处理领域事件
    event_bus = InMemoryEventBus()
    event_handler = OrderEventHandler()
    event_bus.subscribe("OrderProductAdded", event_handler)
    
    events = order.clear_domain_events()
    for event in events:
        event_bus.publish(event)
    
    print()
    
    # 使用规格模式
    expensive_product_spec = PriceGreaterThanSpecification(1000.0)
    laptop_spec = NameContainsSpecification("laptop")
    
    products = [product1, product2, product3]
    
    print("昂贵商品 (价格 > $1000):")
    for product in products:
        if expensive_product_spec.is_satisfied_by(product):
            print(f"- {product.name}: ${product.price}")
    
    print("\n包含'Laptop'的商品:")
    for product in products:
        if laptop_spec.is_satisfied_by(product):
            print(f"- {product.name}: ${product.price}")
    
    # 组合规格
    expensive_laptop_spec = expensive_product_spec & laptop_spec
    print("\n昂贵的笔记本电脑 (价格 > $1000 且包含'Laptop'):")
    for product in products:
        if expensive_laptop_spec.is_satisfied_by(product):
            print(f"- {product.name}: ${product.price}")
    
    # 使用规格评估器
    evaluator = SpecificationEvaluator[Product]()
    expensive_products = evaluator.filter(products, expensive_product_spec)
    print(f"\n规格评估器: 找到 {len(expensive_products)} 个昂贵商品")
    
    print()
    
    # 使用参数值和单位
    power_value = ParameterValue(5.5, "kW", min_value=0.0, max_value=10.0)
    print(f"功率值: {power_value}")
    print(f"功率值单位: {power_value.unit}")
    
    voltage_unit = UnitOfMeasure("kV", "千伏")
    print(f"电压单位: {voltage_unit} ({voltage_unit.name})")
    
    print()
    
    # 使用时间组件
    now = datetime.now()
    time_range = TimeRange(now, TimeService.add_duration(now, hours=2))
    print(f"时间范围: {time_range}")
    print(f"时间范围持续时间: {time_range.duration}")
    
    timestamp = Timestamp(now, precision="second")
    print(f"带精度的时间戳: {timestamp} (精度: {timestamp.precision})")
    
    print()
    
    # 使用单位转换服务
    power_in_watts = UnitConversionService.convert(5.5, "kW", "W", "power")
    print(f"单位转换: 5.5 kW = {power_in_watts} W")
    
    energy_in_kwh = UnitConversionService.convert(3600, "Wh", "kWh", "energy")
    print(f"单位转换: 3600 Wh = {energy_in_kwh} kWh")
    
    print()
    
    # 使用验证服务
    try:
        ValidationService.validate_required_fields({"name": "Test"}, ["name", "age"])
    except ValidationException as e:
        print(f"验证失败: {e}")
    
    try:
        ValidationService.validate_field_range({"age": 150}, "age", 0, 120)
    except ValidationException as e:
        print(f"范围验证失败: {e}")
    
    print("\n=== 示例结束 ===")
