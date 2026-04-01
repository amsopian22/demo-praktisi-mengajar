import subprocess
import argparse
import sys

def run_dbt(layer="all"):
    """
    Menjalankan proses ELT dbt pada direktori dbt_project.
    Sesuai skill, menjaga ACID compliance dilakukan oleh kapabilitas
    transactional materi dbt di PostgreSQL (BEGIN dan COMMIT/ROLLBACK otomatis).
    """
    print(f"Memulai transformasi ELT dbt untuk layer: {layer}")
    
    base_cmd = ["dbt", "run", "--project-dir", "/opt/airflow/dbt_project", "--profiles-dir", "/opt/airflow/dbt_project"]
    
    if layer != "all":
        base_cmd.extend(["--select", f"tag:{layer}"])
        
    try:
        # Menjalankan proses dbt
        result = subprocess.run(base_cmd, check=True, text=True, capture_output=True)
        print("[SUCCESS] Transformasi ELT Berhasil.")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("[ERROR] Transformasi gagal! Postgres Otomatis Rollback.")
        print("Detail Error:")
        print(e.output)
        print(e.stderr)
        # Sesuai skill: Halt pipeline 
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sistem Eksekusi ELT PostgreSQL menggunakan dbt.")
    parser.add_argument("--layer", choices=["silver", "gold", "all"], default="all", help="Pilih layer ELT (silver/gold/all)")
    args = parser.parse_args()
    
    run_dbt(args.layer)
