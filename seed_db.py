import duckdb
import pandas as pd
import numpy as np
import os

# 1. Definir ruta (Render usa la raíz por defecto)
DB_PATH = "housing.db"

def generate_data():
    print("re-generando datos realistas para Madrid...")
    n = 2000
    distritos = {
        "Salamanca": 8500, "Retiro": 7000, "Chamberí": 6500, 
        "Centro": 5500, "Arganzuela": 4500, "Tetuán": 4000, 
        "Latina": 2500, "Usera": 2200, "Villaverde": 1900
    }
    
    names = list(distritos.keys())
    selected_districts = np.random.choice(names, n)
    
    data = []
    for dist in selected_districts:
        m2 = np.random.randint(40, 150)
        precio_base = distritos[dist]
        precio = int(m2 * precio_base * np.random.uniform(0.85, 1.15))
        # Opportunity index: algunos chollos reales (10-15%)
        opp_index = np.random.uniform(0, 15) if np.random.random() > 0.9 else np.random.uniform(0, 5)
        
        data.append({
            "district": dist,
            "area_sqm": m2,
            "price": precio,
            "opportunity_index": round(opp_index, 2),
            "latitude": np.random.uniform(40.38, 40.48),
            "longitude": np.random.uniform(-3.72, -3.65)
        })

    df = pd.DataFrame(data)
    
    # 2. Guardar en DuckDB (Capa Gold)
    df = pd.DataFrame(data)
    
    # Aseguramos que los strings sean strings puros de Python
    df['district'] = df['district'].astype(str)

    # 2. Guardar en DuckDB (Capa Gold)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    con = duckdb.connect(DB_PATH)
    
    # Creamos la tabla directamente desde el diccionario para evitar el lío de tipos de Pandas
    con.execute("CREATE TABLE gold_listings (district VARCHAR, area_sqm INTEGER, price INTEGER, opportunity_index DOUBLE, latitude DOUBLE, longitude DOUBLE)")
    
    # Insertamos los datos de forma masiva
    con.executemany("INSERT INTO gold_listings VALUES (?, ?, ?, ?, ?, ?)", df.values.tolist())
    
    con.close()
    print(f"✅ housing.db generado con éxito con {n} registros.")

if __name__ == "__main__":
    generate_data()