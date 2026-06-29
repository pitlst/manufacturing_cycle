from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from clickhouse_driver import Client
import os
import traceback

app = FastAPI(title="制造周期看板API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CH_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")#10.24.5.59
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))#8123
CH_USER = os.getenv("CLICKHOUSE_USER", "default")#cheakf
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "123")#Swq8855830.
CH_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "default")#dwd


def get_clickhouse_client():
    return Client(
        host=CH_HOST,
        port=CH_PORT,
        user=CH_USER,
        password=CH_PASSWORD,
        database=CH_DATABASE,
    )


class ManufacturingData(BaseModel):
    项目号: str
    项目简称: str
    项目名称: str
    车号: str
    节车号: str
    最早计划开始: Optional[datetime]
    最晚计划结束: Optional[datetime]
    进车计划开始: Optional[datetime]
    进车实际开始: Optional[datetime]
    Q30计划开始: Optional[datetime]
    Q30实际开始: Optional[datetime]
    调车计划开始: Optional[datetime]
    调车实际开始: Optional[datetime]
    连接计划开始: Optional[datetime]
    连接实际开始: Optional[datetime]
    Q40计划开始: Optional[datetime]
    Q40实际开始: Optional[datetime]
    发运计划开始: Optional[datetime]
    发运实际开始: Optional[datetime]
    组装周期天: Optional[float]
    落车周期天: Optional[float]
    调试周期天: Optional[float]
    交付周期天: Optional[float]
    整个制造周期天: Optional[float]


@app.get("/", response_class=FileResponse)
async def root():
    return "index.html"


@app.get("/api/projects")
async def get_projects():
    try:
        client = get_clickhouse_client()
        # 将项目号筛选改为项目简称
        result = client.execute("SELECT DISTINCT `项目简称` FROM manufacturing_cycle ORDER BY `项目简称`")
        return [row[0] for row in result]
    except Exception as e:
        print(f"Error in get_projects: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.disconnect()


@app.get("/api/cars")
async def get_cars(project_abbr: str = Query(..., alias="project_id")):
    try:
        client = get_clickhouse_client()
        result = client.execute(
            "SELECT DISTINCT `车号` FROM manufacturing_cycle WHERE `项目简称` = %(pabbr)s ORDER BY `车号`",
            {'pabbr': project_abbr}
        )
        return [row[0] for row in result]
    except Exception as e:
        print(f"Error in get_cars: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.disconnect()


@app.get("/api/sections")
async def get_sections(project_abbr: str = Query(..., alias="project_id"), car_id: str = Query(...)):
    try:
        client = get_clickhouse_client()
        result = client.execute(
            "SELECT DISTINCT `节车号` FROM manufacturing_cycle WHERE `项目简称` = %(pabbr)s AND `车号` = %(cid)s ORDER BY `节车号`",
            {'pabbr': project_abbr, 'cid': car_id}
        )
        return [row[0] for row in result]
    except Exception as e:
        print(f"Error in get_sections: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.disconnect()


@app.get("/api/data", response_model=ManufacturingData)
async def get_data(
    project_abbr: str = Query(..., alias="project_id"),
    car_id: str = Query(...),
    section_id: str = Query(...)
):
    try:
        client = get_clickhouse_client()
        result = client.execute(
            """
            SELECT
                `项目号`, `项目简称`, `项目名称`, `车号`, `节车号`,
                `最早计划开始`, `最晚计划结束`,
                `进车计划开始`, `进车实际开始`,
                `Q30计划开始`, `Q30实际开始`,
                `调车计划开始`, `调车实际开始`,
                `连接计划开始`, `连接实际开始`,
                `Q40计划开始`, `Q40实际开始`,
                `发运计划开始`, `发运实际开始`,
                `组装周期天`, `落车周期天`, `调试周期天`, `交付周期天`, `整个制造周期天`
            FROM manufacturing_cycle
            WHERE `项目简称` = %(pabbr)s AND `车号` = %(cid)s AND `节车号` = %(sid)s
            LIMIT 1
            """,
            {'pabbr': project_abbr, 'cid': car_id, 'sid': section_id}
        )
        if not result:
            raise HTTPException(status_code=404, detail="未找到匹配的数据")
        
        row = result[0]
        return ManufacturingData(
            项目号=row[0], 项目简称=row[1], 项目名称=row[2], 车号=row[3], 节车号=row[4],
            最早计划开始=row[5], 最晚计划结束=row[6],
            进车计划开始=row[7], 进车实际开始=row[8],
            Q30计划开始=row[9], Q30实际开始=row[10],
            调车计划开始=row[11], 调车实际开始=row[12],
            连接计划开始=row[13], 连接实际开始=row[14],
            Q40计划开始=row[15], Q40实际开始=row[16],
            发运计划开始=row[17], 发运实际开始=row[18],
            组装周期天=row[19], 落车周期天=row[20], 调试周期天=row[21], 交付周期天=row[22], 整个制造周期天=row[23]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_data: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.disconnect()


@app.get("/api/yearly-data")
async def get_yearly_data():
    try:
        client = get_clickhouse_client()
        # 修改为本年数据：最早计划开始或最晚计划结束在今年
        result = client.execute(
            """
            SELECT
                `项目号`, `项目简称`, `车号`, `节车号`,
                `组装周期天`, `落车周期天`, `调试周期天`, `交付周期天`, `整个制造周期天`
            FROM manufacturing_cycle
            WHERE 
                toYear(`最早计划开始`) = toYear(now())
                OR 
                toYear(`最晚计划结束`) = toYear(now())
            ORDER BY `最早计划开始` DESC
            """
        )
        return [
            {
                "项目号": row[0],
                "项目简称": row[1],
                "车号": row[2],
                "节车号": row[3],
                "组装周期天": row[4],
                "落车周期天": row[5],
                "调试周期天": row[6],
                "交付周期天": row[7],
                "整个制造周期天": row[8]
            } for row in result
        ]
    except Exception as e:
        print(f"Error in get_yearly_data: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.disconnect()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
