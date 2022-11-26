import requests
import json
import pandas as pd
from datetime import datetime
import numpy as np
from numpy.compat import long

from fastapi import FastAPI
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware


url = "https://api.thegraph.com/subgraphs/name/aave/protocol-v2"

payload="{\"query\":\"{\\r\\nborrows (first: 100, where: {reserve_: {symbol: \\\"USDC\\\"}}){\\r\\n          txHash\\r\\n  \\t\\t\\t\\tassetPriceUSD\\r\\n  \\t\\t\\t\\treserve{\\r\\n            price{\\r\\n              priceInEth\\r\\n            }\\r\\n          }\\r\\n          user {\\r\\n        \\r\\n        id\\r\\n        liquidationCallHistory {\\r\\n          txHash\\r\\n          collateralAmount\\r\\n          liquidator\\r\\n          collateralAssetPriceUSD\\r\\n          collateralAmount\\r\\n          collateralReserve{\\r\\n            name\\r\\n            symbol\\r\\n            price {\\r\\n              priceInEth\\r\\n              priceSource\\r\\n              priceHistory{\\r\\n                price\\r\\n                timestamp\\r\\n        \\t\\t\\t\\tasset {\\r\\n                  priceInEth\\r\\n                }\\r\\n              }\\r\\n            }\\r\\n            reserveLiquidationThreshold\\r\\n            reserveFactor\\r\\n            reserveLiquidationBonus\\r\\n            availableLiquidity\\r\\n            totalLiquidity\\r\\n            totalLiquidityAsCollateral\\r\\n            liquidityRate\\r\\n            lifetimeLiquidated\\r\\n            lifetimeLiquidity\\r\\n            paramsHistory {\\r\\n              priceInEth\\r\\n              priceInUsd\\r\\n              liquidityRate\\r\\n            }\\r\\n            lifetimeRepayments\\r\\n\\r\\n          }\\r\\n\\r\\n        }\\r\\n      }\\r\\n      amount\\r\\n      borrowRateMode\\r\\n      borrowRate\\r\\n      stableTokenDebt\\r\\n      variableTokenDebt\\r\\n      reserve {\\r\\n        symbol\\r\\n        decimals\\r\\n      }\\r\\n  }\\r\\n}\",\"variables\":{}}"
headers = {
  'Content-Type': 'application/json'
}
def calculateHealthFactor(borrowAmountUsdc, usdcPriceInEth,collateralAmount,collateralInEth,reserveLiquidationThreshold):
  collateralAmount = collateralAmount/pow(10,18)
  collateralInEth = collateralInEth/pow(10,18)
  usdcPriceInEth = usdcPriceInEth/pow(10,18)
  
  healthFactor = (collateralAmount*collateralInEth * reserveLiquidationThreshold) / (borrowAmountUsdc * usdcPriceInEth)
  return healthFactor

def getBorrowDataframe():
    print("Getting Borrow Dataframe")
    response = requests.request("POST", url, headers=headers, data=payload)

    data_list = []
    for item in response.json()['data']['borrows']:
        user_id = item['user']['id']
        borrowAmountUsdc = int(item['amount'])
        usdcPriceInEth = int(item['reserve']['price']['priceInEth'])
        liquidationCallHistory = item['user']['liquidationCallHistory']
        collateralAmount = 0
        reserveLiquidationThreshold = 0
        collateralInEth = 0
        if liquidationCallHistory != []:
            for collateral in liquidationCallHistory:
                collateralAmount = int(collateral['collateralAmount'])
                reserveLiquidationThreshold = int(collateral['collateralReserve']['reserveLiquidationThreshold'])
                collateralInEth = int(collateral['collateralReserve']['price']['priceInEth'])
            data_list.append([user_id,borrowAmountUsdc,usdcPriceInEth,collateralAmount,collateralInEth,reserveLiquidationThreshold])
    
    
    borrow_df = pd.DataFrame(data_list,columns=['userId', 'borrowAmountUsdc', 'usdcPriceInEth','collateralAmount','collateralInEth','reserveLiquidationThreshold'])
    borrow_df.drop_duplicates(inplace=True)
    return borrow_df

def calculateHealthFactor_dataframe(borrow_df):

    print("Calculating Health Factor on dataframe")
    borrow_df["liquidationLevel"] = [np.nan if x == 0 else calculateHealthFactor(borrow_df["borrowAmountUsdc"],borrow_df["usdcPriceInEth"],borrow_df["collateralAmount"],borrow_df["collateralInEth"],borrow_df["reserveLiquidationThreshold"]) for x in borrow_df['collateralAmount']]    
    
    borrow_df.loc[borrow_df['collateralAmount']==0, "liquidationLevel"] = np.nan
    borrow_df.loc[borrow_df['collateralAmount']!=0, "liquidationLevel"] = calculateHealthFactor(borrow_df["borrowAmountUsdc"],borrow_df["usdcPriceInEth"],borrow_df["collateralAmount"],borrow_df["collateralInEth"],borrow_df["reserveLiquidationThreshold"])
    return borrow_df

app=FastAPI()
origins = [
    "http://localhost",
    "http://localhost:8080",

    "http://localhost:8000",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/testdataframe")
def testdataframe():

    borrow_df =  getBorrowDataframe()
    df =  calculateHealthFactor_dataframe(borrow_df)
    value_as_list=[]
    for i in range(len(borrow_df)):
        value_as_list.append([borrow_df['userId'].iloc[i],str(borrow_df['borrowAmountUsdc'].iloc[i]),str(borrow_df['usdcPriceInEth'].iloc[i])
        ,borrow_df['collateralAmount'].iloc[i],str(borrow_df['collateralInEth'].iloc[i]),str(borrow_df['reserveLiquidationThreshold'].iloc[i])
        ,str(borrow_df['liquidationLevel'].iloc[i])])
    
    return {"df":df.to_json(),"values":value_as_list,"columns":borrow_df.columns.tolist()}

    #return Response(content={"df":df.to_json(),"values":value_as_list,"columns":borrow_df.columns.tolist()}, media_type="application/json")
    #return Response(content=df.to_json(), media_type="application/json")






