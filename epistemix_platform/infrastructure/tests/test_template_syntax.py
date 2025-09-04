"""
Tests for CloudFormation template syntax validation.

This module tests all templates for:
- Valid CloudFormation syntax and structure
- JSON/YAML formatting compliance  
- CloudFormation schema validation using cfn-lint
- Template size and complexity limits
- Reference integrity and circular dependency detection
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List, Set

import pytest
from jsonschema import validate, ValidationError


class TestTemplateSyntax:
    """Test suite for CloudFormation template syntax validation."""

    @pytest.fixture(scope="class")
    def cfn_lint_available(self) -> bool:
        """Check if cfn-lint is available."""
        try:
            subprocess.run(["cfn-lint", "--version"], 
                          capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def test_all_templates_valid_json(self, template_files, load_template):
        """Test that all template files are valid JSON."""
        for template_name, template_path in template_files.items():
            try:
                # Use the JSON loader from conftest
                load_template(template_path)
            except json.JSONDecodeError as e:
                pytest.fail(f"Template {template_name} is not valid JSON: {e}")

    def test_cloudformation_format_version(self, template_files, load_template):
        """Test that all templates have correct CloudFormation format version."""
        for template_name, template_path in template_files.items():
            template = load_template(template_path)
            
            assert "AWSTemplateFormatVersion" in template, \
                f"Template {template_name} missing AWSTemplateFormatVersion"
            
            version = template["AWSTemplateFormatVersion"]
            assert version == "2010-09-09", \
                f"Template {template_name} has invalid format version: {version}"

    def test_templates_have_description(self, template_files, load_template):
        """Test that all templates have descriptions."""
        for template_name, template_path in template_files.items():
            template = load_template(template_path)
            
            assert "Description" in template, \
                f"Template {template_name} missing Description"
            
            description = template["Description"]
            assert isinstance(description, str), \
                f"Template {template_name} Description must be string"
            assert len(description.strip()) > 0, \
                f"Template {template_name} Description cannot be empty"

    def test_template_sections_structure(self, template_files, load_template):
        """Test that template sections have correct structure."""
        valid_sections = {
            "AWSTemplateFormatVersion", "Description", "Metadata", 
            "Parameters", "Mappings", "Conditions", "Transform",
            "Resources", "Outputs"
        }
        
        for template_name, template_path in template_files.items():
            template = load_template(template_path)
            
            # Check for invalid top-level sections
            for section in template.keys():
                assert section in valid_sections, \
                    f"Template {template_name} has invalid section: {section}"
            
            # Resources section should exist and not be empty
            assert "Resources" in template, \
                f"Template {template_name} missing Resources section"
            
            resources = template["Resources"]
            assert isinstance(resources, dict), \
                f"Template {template_name} Resources must be a dictionary"
            assert resources, \
                f"Template {template_name} Resources section cannot be empty"

    def test_parameters_section_structure(self, template_files, load_template):
        """Test Parameters section structure and constraints."""
        for template_name, template_path in template_files.items():
            template = load_template(template_path)
            
            if "Parameters" in template:
                parameters = template["Parameters"]
                assert isinstance(parameters, dict), \
                    f"Template {template_name} Parameters must be a dictionary"
                
                for param_name, param_def in parameters.items():
                    # Parameter name validation
                    assert param_name.isalnum() or all(c.isalnum() or c in "_-" for c in param_name), \
                        f"Template {template_name} parameter {param_name} has invalid characters"
                    
                    # Parameter definition structure
                    assert isinstance(param_def, dict), \
                        f"Template {template_name} parameter {param_name} must be a dictionary"
                    
                    assert "Type" in param_def, \
                        f"Template {template_name} parameter {param_name} missing Type"
                    
                    param_type = param_def["Type"]
                    valid_types = [
                        "String", "Number", "List<Number>", "CommaDelimitedList",
                        "AWS::EC2::AvailabilityZone::Name", "AWS::EC2::Image::Id",
                        "AWS::EC2::Instance::Id", "AWS::EC2::KeyPair::KeyName",
                        "AWS::EC2::SecurityGroup::GroupName", "AWS::EC2::SecurityGroup::Id",
                        "AWS::EC2::Subnet::Id", "AWS::EC2::Volume::Id",
                        "AWS::EC2::VPC::Id", "AWS::Route53::HostedZone::Id",
                        "AWS::SSM::Parameter::Name", "AWS::SSM::Parameter::Value<String>",
                        "List<AWS::EC2::AvailabilityZone::Name>", "List<AWS::EC2::Image::Id>",
                        "List<AWS::EC2::Instance::Id>", "List<AWS::EC2::SecurityGroup::GroupName>",
                        "List<AWS::EC2::SecurityGroup::Id>", "List<AWS::EC2::Subnet::Id>",
                        "List<AWS::EC2::Volume::Id>", "List<AWS::EC2::VPC::Id>",
                        "List<AWS::Route53::HostedZone::Id>"
                    ]
                    assert param_type in valid_types, \
                        f"Template {template_name} parameter {param_name} has invalid type: {param_type}"

    def test_resources_section_structure(self, template_files, load_template):
        """Test Resources section structure."""
        for template_name, template_path in template_files.items():
            template = load_template(template_path)
            resources = template["Resources"]
            
            for resource_name, resource_def in resources.items():
                # Resource name validation
                assert resource_name.replace("_", "").replace("-", "").isalnum(), \
                    f"Template {template_name} resource {resource_name} has invalid characters"
                
                # Resource definition structure
                assert isinstance(resource_def, dict), \
                    f"Template {template_name} resource {resource_name} must be a dictionary"
                
                assert "Type" in resource_def, \
                    f"Template {template_name} resource {resource_name} missing Type"
                
                # Type should be valid AWS resource type
                resource_type = resource_def["Type"]
                assert resource_type.startswith("AWS::"), \
                    f"Template {template_name} resource {resource_name} Type should start with AWS::"
                
                # Properties should be a dict if present
                if "Properties" in resource_def:
                    assert isinstance(resource_def["Properties"], dict), \
                        f"Template {template_name} resource {resource_name} Properties must be a dictionary"

    def test_outputs_section_structure(self, template_files, load_template):
        """Test Outputs section structure."""
        for template_name, template_path in template_files.items():
            template = load_template(template_path)
            
            if "Outputs" in template:
                outputs = template["Outputs"]
                assert isinstance(outputs, dict), \
                    f"Template {template_name} Outputs must be a dictionary"
                
                for output_name, output_def in outputs.items():
                    # Output name validation
                    assert output_name.replace("_", "").replace("-", "").isalnum(), \
                        f"Template {template_name} output {output_name} has invalid characters"
                    
                    # Output definition structure
                    assert isinstance(output_def, dict), \
                        f"Template {template_name} output {output_name} must be a dictionary"
                    
                    assert "Description" in output_def, \
                        f"Template {template_name} output {output_name} missing Description"
                    
                    assert "Value" in output_def, \
                        f"Template {template_name} output {output_name} missing Value"

    def test_conditions_section_structure(self, template_files, load_template):
        """Test Conditions section structure."""
        for template_name, template_path in template_files.items():
            template = load_template(template_path)
            
            if "Conditions" in template:
                conditions = template["Conditions"]
                assert isinstance(conditions, dict), \
                    f"Template {template_name} Conditions must be a dictionary"
                
                for condition_name, condition_def in conditions.items():
                    # Condition name validation
                    assert condition_name.replace("_", "").replace("-", "").isalnum(), \
                        f"Template {template_name} condition {condition_name} has invalid characters"
                    
                    # Condition should be a CloudFormation function
                    assert isinstance(condition_def, dict), \
                        f"Template {template_name} condition {condition_name} must be a dictionary"

    def test_template_size_limits(self, template_files):
        """Test that templates don't exceed CloudFormation size limits."""
        for template_name, template_path in template_files.items():
            file_size = template_path.stat().st_size
            
            # CloudFormation template size limit is 460,800 bytes for templates uploaded directly
            # 51,200 bytes for templates uploaded via S3
            # We'll use the direct upload limit
            assert file_size <= 460800, \
                f"Template {template_name} is too large: {file_size} bytes (limit: 460,800)"

    def test_reference_integrity(self, template_files, load_template):
        """Test that all references point to existing resources/parameters."""
        for template_name, template_path in template_files.items():
            template = load_template(template_path)
            
            # Collect all referenceable items
            parameters = set(template.get("Parameters", {}).keys())
            resources = set(template.get("Resources", {}).keys())
            conditions = set(template.get("Conditions", {}).keys())
            
            # AWS pseudo parameters
            pseudo_parameters = {
                "AWS::AccountId", "AWS::NotificationARNs", "AWS::NoValue",
                "AWS::Partition", "AWS::Region", "AWS::StackId", "AWS::StackName",
                "AWS::URLSuffix"
            }
            
            all_referenceable = parameters | resources | conditions | pseudo_parameters
            
            # Check references in the template
            template_str = yaml.dump(template)
            references = self._extract_references(template)
            
            for ref in references:
                if ref not in all_referenceable:
                    pytest.fail(f"Template {template_name} has invalid reference: {ref}")

    def _extract_references(self, obj, refs=None) -> Set[str]:
        """Extract all Ref and GetAtt references from a template object."""
        if refs is None:
            refs = set()
        
        if isinstance(obj, dict):
            if "Ref" in obj:
                refs.add(obj["Ref"])
            elif "Fn::GetAtt" in obj or "GetAtt" in obj:
                # Handle both long and short form
                get_att = obj.get("Fn::GetAtt", obj.get("GetAtt"))
                if isinstance(get_att, list) and len(get_att) > 0:
                    refs.add(get_att[0])  # Resource name
            
            for value in obj.values():
                self._extract_references(value, refs)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_references(item, refs)
        
        return refs

    def test_circular_dependency_detection(self, template_files, load_template):
        """Test for potential circular dependencies in templates."""
        for template_name, template_path in template_files.items():
            template = load_template(template_path)
            resources = template.get("Resources", {})
            
            # Build dependency graph
            dependencies = {}
            for resource_name, resource_def in resources.items():
                deps = self._extract_resource_dependencies(resource_def)
                dependencies[resource_name] = deps
            
            # Check for circular dependencies using DFS
            visited = set()
            rec_stack = set()
            
            def has_cycle(node):
                visited.add(node)
                rec_stack.add(node)
                
                for neighbor in dependencies.get(node, []):
                    if neighbor in resources:  # Only check resource dependencies
                        if neighbor not in visited:
                            if has_cycle(neighbor):
                                return True
                        elif neighbor in rec_stack:
                            return True
                
                rec_stack.remove(node)
                return False
            
            for resource in resources:
                if resource not in visited:
                    if has_cycle(resource):
                        pytest.fail(f"Template {template_name} has circular dependency involving {resource}")

    def _extract_resource_dependencies(self, resource_def: Dict[str, Any]) -> List[str]:
        """Extract resource dependencies from a resource definition."""
        dependencies = []
        
        def find_refs(obj):
            if isinstance(obj, dict):
                if "Ref" in obj:
                    dependencies.append(obj["Ref"])
                elif "Fn::GetAtt" in obj or "GetAtt" in obj:
                    get_att = obj.get("Fn::GetAtt", obj.get("GetAtt"))
                    if isinstance(get_att, list) and len(get_att) > 0:
                        dependencies.append(get_att[0])
                
                for value in obj.values():
                    find_refs(value)
            elif isinstance(obj, list):
                for item in obj:
                    find_refs(item)
        
        find_refs(resource_def)
        return dependencies

    @pytest.mark.skipif(not sys.platform.startswith("linux"), reason="cfn-lint may not be available")
    def test_cfn_lint_validation(self, template_files, cfn_lint_available):
        """Test templates with cfn-lint for CloudFormation compliance."""
        if not cfn_lint_available:
            pytest.skip("cfn-lint not available")
        
        for template_name, template_path in template_files.items():
            try:
                result = subprocess.run(
                    ["cfn-lint", str(template_path)],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    # Filter out warnings and informational messages, focus on errors
                    lines = result.stdout.split('\n')
                    errors = [line for line in lines if 'E' in line and template_path.name in line]
                    
                    if errors:
                        pytest.fail(f"Template {template_name} failed cfn-lint validation:\n" + 
                                  '\n'.join(errors))
            
            except FileNotFoundError:
                pytest.skip("cfn-lint command not found")

    def test_json_serializable(self, template_files, load_template):
        """Test that templates can be serialized to JSON (CloudFormation requirement)."""
        for template_name, template_path in template_files.items():
            template = load_template(template_path)
            
            try:
                json.dumps(template)
            except (TypeError, ValueError) as e:
                pytest.fail(f"Template {template_name} is not JSON serializable: {e}")

    def test_parameter_constraints_valid(self, template_files, load_template):
        """Test that parameter constraints are valid."""
        for template_name, template_path in template_files.items():
            template = load_template(template_path)
            parameters = template.get("Parameters", {})
            
            for param_name, param_def in parameters.items():
                # Check constraint properties
                if "MinLength" in param_def:
                    min_length = param_def["MinLength"]
                    assert isinstance(min_length, int) and min_length >= 0, \
                        f"Template {template_name} parameter {param_name} MinLength must be non-negative integer"
                
                if "MaxLength" in param_def:
                    max_length = param_def["MaxLength"]
                    assert isinstance(max_length, int) and max_length >= 0, \
                        f"Template {template_name} parameter {param_name} MaxLength must be non-negative integer"
                
                if "MinLength" in param_def and "MaxLength" in param_def:
                    assert param_def["MinLength"] <= param_def["MaxLength"], \
                        f"Template {template_name} parameter {param_name} MinLength must be <= MaxLength"
                
                if "AllowedValues" in param_def:
                    allowed_values = param_def["AllowedValues"]
                    assert isinstance(allowed_values, list), \
                        f"Template {template_name} parameter {param_name} AllowedValues must be a list"
                    assert len(allowed_values) > 0, \
                        f"Template {template_name} parameter {param_name} AllowedValues cannot be empty"
                
                if "AllowedPattern" in param_def:
                    pattern = param_def["AllowedPattern"]
                    assert isinstance(pattern, str), \
                        f"Template {template_name} parameter {param_name} AllowedPattern must be a string"
                    
                    # Test that pattern is valid regex
                    import re
                    try:
                        re.compile(pattern)
                    except re.error as e:
                        pytest.fail(f"Template {template_name} parameter {param_name} has invalid regex pattern: {e}")

    def test_function_syntax(self, template_files, load_template):
        """Test CloudFormation intrinsic function syntax."""
        valid_functions = {
            "Ref", "Fn::GetAtt", "Fn::Join", "Fn::Split", "Fn::Select", 
            "Fn::Sub", "Fn::Base64", "Fn::GetAZs", "Fn::ImportValue",
            "Fn::FindInMap", "Fn::If", "Fn::Not", "Fn::Equals",
            "Fn::And", "Fn::Or", "Condition"
        }
        
        for template_name, template_path in template_files.items():
            template = load_template(template_path)
            functions_found = self._find_functions(template)
            
            for func in functions_found:
                if not any(func == vf or func.startswith(f"{vf}:") for vf in valid_functions):
                    pytest.fail(f"Template {template_name} uses invalid function: {func}")

    def _find_functions(self, obj, functions=None) -> Set[str]:
        """Find all CloudFormation functions used in a template."""
        if functions is None:
            functions = set()
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.startswith("Fn::") or key == "Ref" or key == "Condition":
                    functions.add(key)
                self._find_functions(value, functions)
        elif isinstance(obj, list):
            for item in obj:
                self._find_functions(item, functions)
        
        return functions