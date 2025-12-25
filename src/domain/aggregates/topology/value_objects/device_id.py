from domain.common.value_objects.id_value_objects import EntityId

class DeviceId(EntityId):
    """设备标识符值对象
    管理设备ID的生成和回收，所有设备类型共享同一个ID池
    """

    # 类变量：共享ID池 - 使用全局字典存储，确保跨实例共享
    _id_pool = {
        'used': set(),  # 已使用的ID集合
        'recycled': set(),  # 已回收的ID集合
        'next': 1  # 下一个要分配的ID
    }

    def __init__(self, value):
        """初始化设备ID
        Args:
            value: 设备ID字符串
        """
        super().__init__(value)

    @classmethod
    def generate(cls, device_type=None):
        """生成设备ID，所有设备类型共享同一个ID池
        Args:
            device_type: 设备类型字符串（用于兼容旧代码，不影响ID生成）
        Returns:
            设备ID对象
        """
        id_pool = cls._id_pool
        
        # 优先使用回收的ID
        if id_pool['recycled']:
            # 获取最小的回收ID
            id_num = min(id_pool['recycled'])
            # 从回收池移除
            id_pool['recycled'].remove(id_num)
        else:
            # 使用下一个可用ID
            id_num = id_pool['next']
            id_pool['next'] += 1

        # 添加到已使用ID集合
        id_pool['used'].add(id_num)

        # 生成ID：只包含数字
        return cls(str(id_num))

    @classmethod
    def recycle_id(cls, device_id, device_type=None):
        """回收设备ID，返回到共享ID池
        Args:
            device_id: 设备ID字符串
            device_type: 设备类型名称（用于兼容旧代码，不影响ID回收）
        """
        id_pool = cls._id_pool
        
        try:
            # 提取数字部分
            id_num = int(device_id)
            # 如果ID在已使用集合中，将其移到回收池
            if id_num in id_pool['used']:
                id_pool['used'].remove(id_num)
                id_pool['recycled'].add(id_num)
        except ValueError:
            # 如果ID格式不正确，忽略回收
            pass

    def __str__(self):
        """返回设备ID字符串"""
        return self.value
