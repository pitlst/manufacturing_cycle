from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
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

CH_HOST = os.getenv("CLICKHOUSE_HOST", "10.24.5.59")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
CH_USER = os.getenv("CLICKHOUSE_USER", "cheakf")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "Swq8855830.")
CH_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "dwd")


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
    最早计划开始: datetime | None
    最晚计划结束: datetime | None
    进车计划开始: datetime | None
    进车实际开始: datetime | None
    Q30计划开始: datetime | None
    Q30实际开始: datetime | None
    调车计划开始: datetime | None
    调车实际开始: datetime | None
    连接计划开始: datetime | None
    连接实际开始: datetime | None
    Q40计划开始: datetime | None
    Q40实际开始: datetime | None
    发运计划开始: datetime | None
    发运实际开始: datetime | None
    组装周期天: float | None
    落车周期天: float | None
    调试周期天: float | None
    交付周期天: float | None
    整个制造周期天: float | None


@app.get("/", response_class=FileResponse)
async def root():
    return "index.html"


@app.get("/api/projects")
async def get_projects() -> list[str]:
    try:
        client = get_clickhouse_client()
        # 将项目号筛选改为项目简称
        result = client.query_dataframe("SELECT DISTINCT `项目简称` FROM manufacturing_cycle ORDER BY `项目简称`")
        return [str(row['项目简称']) for _, row in result.iterrows()]
    except Exception as e:
        print(f"Error in get_projects: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.disconnect()


@app.get("/api/cars")
async def get_cars(project_abbr: str = Query(..., alias="project_id")) -> list[str]:
    try:
        client = get_clickhouse_client()
        result = client.query_dataframe(
            "SELECT DISTINCT `车号` FROM manufacturing_cycle WHERE `项目简称` = %(pabbr)s ORDER BY `车号`",
            {'pabbr': project_abbr}
        )
        return [str(row['车号']) for _, row in result.iterrows()]
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
        result = client.query_dataframe(
            "SELECT DISTINCT `节车号` FROM manufacturing_cycle WHERE `项目简称` = %(pabbr)s AND `车号` = %(cid)s ORDER BY `节车号`",
            {'pabbr': project_abbr, 'cid': car_id}
        )
        return [str(row['车号']) for _, row in result.iterrows()]
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
        result = client.query_dataframe(
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
        if len(result) == 0:
            raise HTTPException(status_code=404, detail="未找到匹配的数据")

        return ManufacturingData(
            项目号=result['项目号'][0],
            项目简称=result['项目简称'][0],
            项目名称=result['项目名称'][0],
            车号=result['车号'][0],
            节车号=result['节车号'][0],
            最早计划开始=result['最早计划开始'][0],
            最晚计划结束=result['最晚计划结束'][0],
            进车计划开始=result['进车计划开始'][0],
            进车实际开始=result['进车实际开始'][0],
            Q30计划开始=result['Q30计划开始'][0],
            Q30实际开始=result['Q30实际开始'][0],
            调车计划开始=result['调车计划开始'][0],
            调车实际开始=result['调车实际开始'][0],
            连接计划开始=result['连接计划开始'][0],
            连接实际开始=result['连接实际开始'][0],
            Q40计划开始=result['Q40计划开始'][0],
            Q40实际开始=result['Q40实际开始'][0],
            发运计划开始=result['发运计划开始'][0],
            发运实际开始=result['发运实际开始'][0],
            组装周期天=result['组装周期天'][0],
            落车周期天=result['落车周期天'][0],
            调试周期天=result['调试周期天'][0],
            交付周期天=result['交付周期天'][0],
            整个制造周期天=result['整个制造周期天'][0]
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
        result = client.query_dataframe(
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
                "项目号": row['项目号'],
                "项目简称": row['项目简称'],
                "车号": row['车号'],
                "节车号": row['节车号'],
                "组装周期天": row['组装周期天'],
                "落车周期天": row['落车周期天'],
                "调试周期天": row['调试周期天'],
                "交付周期天": row['交付周期天'],
                "整个制造周期天": row['整个制造周期天']
            } for _, row in result.iterrows()
        ]
    except Exception as e:
        print(f"Error in get_yearly_data: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        client.disconnect()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=18000)
