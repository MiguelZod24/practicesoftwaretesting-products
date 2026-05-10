#!/usr/bin/env python3
"""
Script de corrección automática de problemas comunes
Formatea código, organiza imports y corrige problemas simples
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, description: str) -> bool:
    """Ejecuta un comando y muestra el resultado"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completado")
            if result.stdout:
                print(f"   {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Error en {description}: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error ejecutando {description}: {e}")
        return False


def main():
    project_root = Path(".")
    
    print("🚀 Iniciando corrección automática de código...")
    print(f"📁 Proyecto: {project_root.absolute()}")
    print()
    
    # 1. Formatear con Black
    run_command(["black", ".", "--line-length=88"], "Formateando código con Black")
    
    # 2. Organizar imports con isort
    run_command(["isort", ".", "--profile=black"], "Organizando imports con isort")
    
    # 3. Corregir problemas simples con autopep8 (opcional)
    # run_command(["autopep8", "--in-place", "--recursive", "."], "Corrigiendo estilo con autopep8")
    
    print("\n✨ Corrección automática completada!")
    print("💡 Ejecuta 'python scripts/analyze_code.py' para ver el reporte de análisis")


if __name__ == "__main__":
    main()
