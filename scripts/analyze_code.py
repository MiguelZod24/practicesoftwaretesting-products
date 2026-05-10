#!/usr/bin/env python3
"""
Script de análisis automatizado de código Python-Playwright
Ejecuta múltiples herramientas de análisis y genera un reporte consolidado
"""

import subprocess
import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class CodeAnalyzer:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root.absolute()),
            "tools": {},
            "summary": {"total_issues": 0, "critical_issues": 0}
        }

    def run_bandit(self) -> Dict[str, Any]:
        """Ejecuta análisis de seguridad con Bandit"""
        print("🔒 Ejecutando análisis de seguridad (Bandit)...")
        try:
            result = subprocess.run(
                ["bandit", "-r", ".", "-f", "json", "-o", "bandit-report.json"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                with open(self.project_root / "bandit-report.json", "r") as f:
                    bandit_data = json.load(f)
                
                issues = [r for r in bandit_data.get("results", []) if r.get("issue_severity") in ["HIGH", "MEDIUM"]]
                self.report["tools"]["bandit"] = {
                    "status": "success",
                    "issues": issues,
                    "total_issues": len(issues),
                    "high_severity": len([i for i in issues if i.get("issue_severity") == "HIGH"])
                }
                print(f"✅ Bandit: {len(issues)} problemas de seguridad encontrados")
            else:
                self.report["tools"]["bandit"] = {
                    "status": "error",
                    "error": result.stderr
                }
                print(f"❌ Bandit: Error en ejecución")
                
        except Exception as e:
            self.report["tools"]["bandit"] = {"status": "error", "error": str(e)}
            print(f"❌ Bandit: {e}")

    def run_flake8(self) -> Dict[str, Any]:
        """Ejecuta análisis de estilo con Flake8"""
        print("📝 Ejecutando análisis de estilo (Flake8)...")
        try:
            result = subprocess.run(
                ["flake8", ".", "--format=json"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.stdout:
                # Parsear salida de flake8
                issues = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(':')
                        if len(parts) >= 4:
                            issues.append({
                                "file": parts[0],
                                "line": int(parts[1]),
                                "column": int(parts[2]),
                                "message": parts[3].strip()
                            })
                
                self.report["tools"]["flake8"] = {
                    "status": "success",
                    "issues": issues,
                    "total_issues": len(issues)
                }
                print(f"✅ Flake8: {len(issues)} problemas de estilo encontrados")
            else:
                self.report["tools"]["flake8"] = {
                    "status": "success",
                    "issues": [],
                    "total_issues": 0
                }
                print("✅ Flake8: Sin problemas de estilo")
                
        except Exception as e:
            self.report["tools"]["flake8"] = {"status": "error", "error": str(e)}
            print(f"❌ Flake8: {e}")

    def run_pylint(self) -> Dict[str, Any]:
        """Ejecuta análisis completo con Pylint"""
        print("🔍 Ejecutando análisis completo (Pylint)...")
        try:
            result = subprocess.run(
                ["pylint", ".", "--output-format=json", "--reports=no"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if result.stdout:
                try:
                    issues = json.loads(result.stdout)
                    self.report["tools"]["pylint"] = {
                        "status": "success",
                        "issues": issues,
                        "total_issues": len(issues),
                        "score": self._extract_pylint_score(result.stderr)
                    }
                    print(f"✅ Pylint: {len(issues)} problemas encontrados")
                except json.JSONDecodeError:
                    self.report["tools"]["pylint"] = {
                        "status": "success",
                        "issues": [],
                        "total_issues": 0,
                        "raw_output": result.stdout
                    }
                    print("✅ Pylint: Análisis completado")
            else:
                self.report["tools"]["pylint"] = {"status": "success", "issues": [], "total_issues": 0}
                
        except Exception as e:
            self.report["tools"]["pylint"] = {"status": "error", "error": str(e)}
            print(f"❌ Pylint: {e}")

    def run_mypy(self) -> Dict[str, Any]:
        """Ejecuta análisis de tipos con MyPy"""
        print("🏷️ Ejecutando análisis de tipos (MyPy)...")
        try:
            result = subprocess.run(
                ["mypy", ".", "--show-error-codes", "--no-error-summary"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            issues = []
            for line in result.stdout.strip().split('\n'):
                if line and ':' in line:
                    parts = line.split(':', 3)
                    if len(parts) >= 4:
                        issues.append({
                            "file": parts[0],
                            "line": int(parts[1]),
                            "type": parts[2].strip(),
                            "message": parts[3].strip()
                        })
            
            self.report["tools"]["mypy"] = {
                "status": "success",
                "issues": issues,
                "total_issues": len(issues)
            }
            print(f"✅ MyPy: {len(issues)} problemas de tipos encontrados")
            
        except Exception as e:
            self.report["tools"]["mypy"] = {"status": "error", "error": str(e)}
            print(f"❌ MyPy: {e}")

    def run_safety(self) -> Dict[str, Any]:
        """Verifica vulnerabilidades en dependencias"""
        print("🛡️ Verificando seguridad de dependencias (Safety)...")
        try:
            result = subprocess.run(
                ["safety", "check", "--json", "--output", "safety-report.json"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            
            if os.path.exists(self.project_root / "safety-report.json"):
                with open(self.project_root / "safety-report.json", "r") as f:
                    safety_data = json.load(f)
                
                vulnerabilities = safety_data.get("vulnerabilities", [])
                self.report["tools"]["safety"] = {
                    "status": "success",
                    "vulnerabilities": vulnerabilities,
                    "total_vulnerabilities": len(vulnerabilities)
                }
                print(f"✅ Safety: {len(vulnerabilities)} vulnerabilidades encontradas")
            else:
                self.report["tools"]["safety"] = {"status": "success", "vulnerabilities": [], "total_vulnerabilities": 0}
                print("✅ Safety: Sin vulnerabilidades")
                
        except Exception as e:
            self.report["tools"]["safety"] = {"status": "error", "error": str(e)}
            print(f"❌ Safety: {e}")

    def _extract_pylint_score(self, stderr: str) -> float:
        """Extrae el score de pylint del stderr"""
        for line in stderr.split('\n'):
            if "rated at" in line:
                try:
                    return float(line.split("rated at")[1].split("/")[0].strip())
                except:
                    pass
        return 0.0

    def generate_summary(self):
        """Genera resumen del análisis"""
        total_issues = 0
        critical_issues = 0
        
        for tool, data in self.report["tools"].items():
            if data.get("status") == "success":
                if tool == "bandit":
                    total_issues += data.get("total_issues", 0)
                    critical_issues += data.get("high_severity", 0)
                elif tool == "safety":
                    total_issues += data.get("total_vulnerabilities", 0)
                    critical_issues += data.get("total_vulnerabilities", 0)
                else:
                    total_issues += data.get("total_issues", 0)
        
        self.report["summary"]["total_issues"] = total_issues
        self.report["summary"]["critical_issues"] = critical_issues

    def save_report(self, filename: str = "code_analysis_report.json"):
        """Guarda el reporte en un archivo JSON"""
        with open(self.project_root / filename, "w") as f:
            json.dump(self.report, f, indent=2, default=str)
        print(f"📊 Reporte guardado en: {filename}")

    def print_summary(self):
        """Imprime resumen en consola"""
        print("\n" + "="*60)
        print("📊 RESUMEN DEL ANÁLISIS DE CÓDIGO")
        print("="*60)
        
        for tool, data in self.report["tools"].items():
            status_emoji = "✅" if data.get("status") == "success" else "❌"
            print(f"{status_emoji} {tool.upper()}: ", end="")
            
            if data.get("status") == "success":
                if tool == "bandit":
                    issues = data.get("total_issues", 0)
                    high = data.get("high_severity", 0)
                    print(f"{issues} problemas ({high} críticos)")
                elif tool == "safety":
                    vulns = data.get("total_vulnerabilities", 0)
                    print(f"{vulns} vulnerabilidades")
                elif tool == "pylint":
                    issues = data.get("total_issues", 0)
                    score = data.get("score", 0)
                    print(f"{issues} problemas (Score: {score}/10)")
                else:
                    issues = data.get("total_issues", 0)
                    print(f"{issues} problemas")
            else:
                print(f"Error - {data.get('error', 'Unknown error')}")
        
        print(f"\n🔥 TOTAL: {self.report['summary']['total_issues']} problemas")
        print(f"⚠️  CRÍTICOS: {self.report['summary']['critical_issues']} problemas")
        print("="*60)

    def run_all_analysis(self):
        """Ejecuta todos los análisis"""
        print("🚀 Iniciando análisis completo de código...")
        print(f"📁 Proyecto: {self.project_root.absolute()}")
        print()
        
        # Ejecutar todos los análisis
        self.run_bandit()
        self.run_flake8()
        self.run_pylint()
        self.run_mypy()
        self.run_safety()
        
        # Generar resumen y guardar reporte
        self.generate_summary()
        self.save_report()
        self.print_summary()


if __name__ == "__main__":
    analyzer = CodeAnalyzer()
    analyzer.run_all_analysis()
