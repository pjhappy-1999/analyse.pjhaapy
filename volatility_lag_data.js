const volatility_lag_data = {
  "lags": [
    0,
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8
  ],
  "series": {
    "oil": [
      -0.0884,
      -0.1052,
      -0.0015,
      -0.024,
      0.016,
      -0.0106,
      -0.1594,
      0.0312,
      -0.0204
    ],
    "wheat": [
      -0.0148,
      0.308,
      0.3397,
      -0.039,
      -0.1301,
      -0.1262,
      -0.1186,
      0.0139,
      0.2128
    ],
    "maize": [
      -0.0544,
      0.1678,
      0.013,
      -0.05,
      -0.167,
      -0.0331,
      0.019,
      0.1151,
      0.3646
    ],
    "soybeans": [
      -0.0516,
      -0.0107,
      -0.0328,
      0.1043,
      0.0849,
      0.0624,
      0.1386,
      -0.1069,
      -0.1449
    ],
    "cotton": [
      0.0196,
      0.2171,
      0.1337,
      -0.1429,
      -0.0455,
      0.0285,
      0.0323,
      0.1342,
      -0.015
    ],
    "palm_oil": [
      -0.0367,
      0.0673,
      0.0962,
      0.1676,
      0.2902,
      0.225,
      0.0374,
      -0.0046,
      -0.133
    ]
  },
  "analysis": [
    {
      "commodity": "oil",
      "best_lag": 6,
      "correlation": -0.1594
    },
    {
      "commodity": "wheat",
      "best_lag": 2,
      "correlation": 0.3397
    },
    {
      "commodity": "maize",
      "best_lag": 8,
      "correlation": 0.3646
    },
    {
      "commodity": "soybeans",
      "best_lag": 8,
      "correlation": -0.1449
    },
    {
      "commodity": "cotton",
      "best_lag": 1,
      "correlation": 0.2171
    },
    {
      "commodity": "palm_oil",
      "best_lag": 4,
      "correlation": 0.2902
    }
  ]
};