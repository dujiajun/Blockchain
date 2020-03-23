import ecdsa


class Params:
    PERIOD_FOR_ONE_CONSENSUS = 1 * 5  # we hope 10 secs for one consensus
    CURVE = ecdsa.SECP256k1
    SLOW_PEERS_IN_NETWORK = 20. / 100
    SLOWER_PEERS_IN_NETWORK = 10. / 100
    FIX_BLOCK_REWARD = 500
    INITIAL_DIFFICULTY_BITS = 18