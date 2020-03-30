import ecdsa


class Params:
    """
    全局参数
    """
    CURVE = ecdsa.SECP256k1  # 使用的椭圆曲线
    MINING_REWARDS = 500  # 挖矿收益
    DIFFICULTY_BITS = 18  # 初始难度
    INITIAL_MONEY = 500  # 创始区块奖励