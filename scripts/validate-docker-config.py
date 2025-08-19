#!/usr/bin/env python3
"""
Docker Configuration Validator

This script validates Docker Compose configurations for common issues,
particularly network mode conflicts and Raspberry Pi compatibility.
"""

import yaml
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple

class DockerConfigValidator:
    """Validates Docker Compose configurations for common issues."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
    
    def validate_file(self, compose_file: str) -> Tuple[List[str], List[str], List[str]]:
        """
        Validate a Docker Compose file.
        
        Args:
            compose_file: Path to docker-compose.yml file
            
        Returns:
            Tuple of (errors, warnings, info)
        """
        if not os.path.exists(compose_file):
            self.errors.append(f"File not found: {compose_file}")
            return self.errors, self.warnings, self.info
        
        try:
            with open(compose_file, 'r') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parsing error in {compose_file}: {e}")
            return self.errors, self.warnings, self.info
        
        self.info.append(f"Validating: {compose_file}")
        
        # Validate services
        if 'services' in config:
            for service_name, service_config in config['services'].items():
                self._validate_service(service_name, service_config, compose_file)
        
        return self.errors, self.warnings, self.info
    
    def _validate_service(self, service_name: str, service_config: Dict[str, Any], compose_file: str):
        """Validate a single service configuration."""
        
        # Check for network mode conflicts
        self._check_network_mode_conflicts(service_name, service_config, compose_file)
        
        # Check for Raspberry Pi compatibility
        self._check_rpi_compatibility(service_name, service_config, compose_file)
        
        # Check for resource limits
        self._check_resource_limits(service_name, service_config, compose_file)
        
        # Check for health checks
        self._check_health_checks(service_name, service_config, compose_file)
    
    def _check_network_mode_conflicts(self, service_name: str, service_config: Dict[str, Any], compose_file: str):
        """Check for network mode and port mapping conflicts."""
        
        network_mode = service_config.get('network_mode')
        ports = service_config.get('ports')
        
        if network_mode == 'host' and ports:
            self.errors.append(
                f"❌ {compose_file}:{service_name} - "
                f"Cannot use 'ports' with 'network_mode: host'. "
                f"Host networking bypasses Docker's port mapping."
            )
        
        if network_mode == 'host':
            self.info.append(
                f"ℹ️  {compose_file}:{service_name} - "
                f"Using host networking. Service will bind directly to host ports."
            )
        
        # Check for privileged mode with host networking (common for Bluetooth)
        privileged = service_config.get('privileged')
        if network_mode == 'host' and privileged:
            self.info.append(
                f"ℹ️  {compose_file}:{service_name} - "
                f"Host networking + privileged mode detected (likely for Bluetooth access)."
            )
    
    def _check_rpi_compatibility(self, service_name: str, service_config: Dict[str, Any], compose_file: str):
        """Check for Raspberry Pi compatibility issues."""
        
        # Check for ARM-incompatible images
        image = service_config.get('image', '')
        arm_incompatible_images = [
            'mcr.microsoft.com',  # Microsoft images often x86 only
            'oraclelinux',        # Oracle Linux typically x86 only
        ]
        
        for incompatible in arm_incompatible_images:
            if incompatible in image:
                self.warnings.append(
                    f"⚠️  {compose_file}:{service_name} - "
                    f"Image '{image}' may not be compatible with ARM architecture (Raspberry Pi)."
                )
        
        # Check for excessive resource limits
        deploy = service_config.get('deploy', {})
        resources = deploy.get('resources', {})
        limits = resources.get('limits', {})
        
        if 'memory' in limits:
            memory_str = limits['memory']
            if isinstance(memory_str, str):
                # Parse memory limit (e.g., "512M", "1G")
                if memory_str.endswith('G'):
                    memory_gb = float(memory_str[:-1])
                    if memory_gb > 2:
                        self.warnings.append(
                            f"⚠️  {compose_file}:{service_name} - "
                            f"Memory limit {memory_str} may be too high for Raspberry Pi (typically 1-8GB total)."
                        )
                elif memory_str.endswith('M'):
                    memory_mb = float(memory_str[:-1])
                    if memory_mb > 1024:
                        self.warnings.append(
                            f"⚠️  {compose_file}:{service_name} - "
                            f"Memory limit {memory_str} may be high for Raspberry Pi."
                        )
    
    def _check_resource_limits(self, service_name: str, service_config: Dict[str, Any], compose_file: str):
        """Check for appropriate resource limits."""
        
        deploy = service_config.get('deploy', {})
        resources = deploy.get('resources', {})
        
        if not resources:
            if 'rpi' in compose_file.lower() or 'raspberry' in compose_file.lower():
                self.warnings.append(
                    f"⚠️  {compose_file}:{service_name} - "
                    f"No resource limits defined. Consider adding limits for Raspberry Pi deployment."
                )
        else:
            self.info.append(
                f"ℹ️  {compose_file}:{service_name} - "
                f"Resource limits configured: {resources}"
            )
    
    def _check_health_checks(self, service_name: str, service_config: Dict[str, Any], compose_file: str):
        """Check for health check configurations."""
        
        healthcheck = service_config.get('healthcheck')
        network_mode = service_config.get('network_mode')
        
        if healthcheck and network_mode == 'host':
            test_cmd = healthcheck.get('test', [])
            if isinstance(test_cmd, list) and len(test_cmd) > 1:
                # Check if health check URL uses localhost (correct for host networking)
                health_url = ' '.join(test_cmd)
                if 'localhost' not in health_url and '127.0.0.1' not in health_url:
                    self.warnings.append(
                        f"⚠️  {compose_file}:{service_name} - "
                        f"Health check should use 'localhost' with host networking mode."
                    )
    
    def print_results(self):
        """Print validation results."""
        
        print("🔍 Docker Configuration Validation Results")
        print("=" * 50)
        
        if self.info:
            print("\n📋 Information:")
            for info in self.info:
                print(f"  {info}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  {error}")
        
        print("\n" + "=" * 50)
        
        if self.errors:
            print("❌ Validation FAILED - Please fix errors before deployment")
            return False
        elif self.warnings:
            print("⚠️  Validation PASSED with warnings - Review warnings before deployment")
            return True
        else:
            print("✅ Validation PASSED - Configuration looks good")
            return True

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate Docker Compose configurations')
    parser.add_argument('files', nargs='*', help='Docker Compose files to validate')
    parser.add_argument('--all', action='store_true', help='Validate all docker-compose files in current directory')
    
    args = parser.parse_args()
    
    files_to_validate = []
    
    if args.all:
        # Find all docker-compose files
        for pattern in ['docker-compose*.yml', 'docker-compose*.yaml']:
            files_to_validate.extend(Path('.').glob(pattern))
    elif args.files:
        files_to_validate = args.files
    else:
        # Default files to check
        default_files = [
            'docker-compose.yml',
            'docker-compose.prod.yml',
            'docker-compose.rpi.yml',
            'docker-compose.dev.yml',
            'docker-compose.staging.yml'
        ]
        files_to_validate = [f for f in default_files if os.path.exists(f)]
    
    if not files_to_validate:
        print("❌ No Docker Compose files found to validate")
        sys.exit(1)
    
    validator = DockerConfigValidator()
    overall_success = True
    
    for compose_file in files_to_validate:
        errors, warnings, info = validator.validate_file(str(compose_file))
        if errors:
            overall_success = False
    
    success = validator.print_results()
    
    if not success:
        sys.exit(1)
    
    print(f"\n🎉 Validated {len(files_to_validate)} Docker Compose file(s)")

if __name__ == '__main__':
    main()