"""
AI-Powered Parameter Extractor

Uses LLM to intelligently extract and describe parameters from:
- SCL JSON files (design intent)
- Generated Python code (implementation)
- STEP files (geometry)

This provides the most accurate parameter extraction with natural language descriptions.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.append(str(Path(__file__).parent.parent))

from services.gemini_service import call_gemini


AI_PARAMETER_EXTRACTION_PROMPT = """You are a CAD parameter extraction expert. Analyze the provided CAD data and extract ALL meaningful, editable design parameters.

CRITICAL RULES:
1. Extract HIGH-LEVEL design parameters (diameter, height, width, thickness, etc.)
2. DO NOT extract low-level implementation details (normalized coordinates, scale factors)
3. Provide clear, user-friendly descriptions
4. Include realistic min/max ranges based on the shape type
5. Output ONLY valid JSON - no markdown, no explanations

OUTPUT FORMAT (JSON):
{
  "parameters": [
    {
      "name": "diameter",
      "value": 20.0,
      "type": "float",
      "description": "Cylinder outer diameter",
      "unit": "mm",
      "min": 1.0,
      "max": 500.0,
      "category": "dimension",
      "priority": "high"
    },
    {
      "name": "height",
      "value": 50.0,
      "type": "float",
      "description": "Cylinder height (length along Z-axis)",
      "unit": "mm",
      "min": 0.5,
      "max": 1000.0,
      "category": "dimension",
      "priority": "high"
    }
  ],
  "shape_type": "Cylinder",
  "design_intent": "Simple solid cylinder for mechanical applications"
}

CATEGORIES:
- "dimension": Main size parameters (length, width, height, diameter, radius, thickness)
- "position": Location offsets (X, Y, Z translations)
- "rotation": Angular orientation (Euler angles)
- "feature": Additional features (holes, fillets, chamfers, patterns)

PRIORITY LEVELS:
- "high": Primary dimensions users want to change (diameter, height, length)
- "medium": Secondary parameters (positions, small features)
- "low": Fine-tuning parameters (small fillets, minor offsets)

EXAMPLES OF GOOD PARAMETERS:
✓ "outer_diameter": 30mm (clear, meaningful)
✓ "wall_thickness": 2mm (derived but important)
✓ "hole_diameter": 5mm (feature dimension)
✓ "fillet_radius": 1mm (post-processing)

BAD PARAMETERS TO AVOID:
✗ "sketch_scale": 20.0 (internal implementation)
✗ "circle_1_radius": 0.5 (normalized, meaningless to user)
✗ "extrude_depth_towards_normal": 2.5 (normalized, confusing)
✗ "moveTo_x": 10.0 (too low-level)

Now extract parameters from this CAD data:
"""


class AIParameterExtractor:
    """AI-powered parameter extraction using LLM"""
    
    def __init__(self):
        self.last_extraction = None
    
    def extract_from_json(self, json_file_path: str) -> Dict[str, Any]:
        """Extract parameters from SCL JSON using AI"""
        
        json_path = Path(json_file_path)
        
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file not found: {json_file_path}")
        
        with open(json_path, 'r') as f:
            json_data = json.load(f)
        
        # Build prompt with JSON data
        prompt = AI_PARAMETER_EXTRACTION_PROMPT + f"\n\nSCL JSON:\n```json\n{json.dumps(json_data, indent=2)}\n```"
        
        # Call LLM
        response = call_gemini(prompt, temperature=0.1, max_tokens=4096)
        
        # Parse response
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = response.strip()
            if '```json' in json_str:
                json_str = json_str.split('```json')[1].split('```')[0].strip()
            elif '```' in json_str:
                json_str = json_str.split('```')[1].split('```')[0].strip()
            
            result = json.loads(json_str)
            
            # Add metadata
            result['file'] = str(json_path)
            result['json_data'] = json_data
            result['total_count'] = len(result.get('parameters', []))
            result['extraction_method'] = 'ai'
            result['units'] = json_data.get('units', 'mm')
            
            self.last_extraction = result
            return result
            
        except json.JSONDecodeError as e:
            # Fallback: return error with raw response
            return {
                'error': True,
                'message': f'Failed to parse AI response: {str(e)}',
                'raw_response': response,
                'file': str(json_path),
                'parameters': [],
                'total_count': 0
            }
    
    def extract_from_python(self, py_file_path: str, json_file_path: Optional[str] = None) -> Dict[str, Any]:
        """Extract parameters from generated Python code using AI"""
        
        py_path = Path(py_file_path)
        
        if not py_path.exists():
            raise FileNotFoundError(f"Python file not found: {py_file_path}")
        
        with open(py_path, 'r') as f:
            python_code = f.read()
        
        # If JSON is available, include it for context
        context = ""
        if json_file_path and Path(json_file_path).exists():
            with open(json_file_path, 'r') as f:
                json_data = json.load(f)
            context = f"\n\nOriginal SCL JSON (for context):\n```json\n{json.dumps(json_data, indent=2)}\n```"
        
        # Build prompt
        prompt = AI_PARAMETER_EXTRACTION_PROMPT + f"\n\nGenerated CadQuery Python Code:\n```python\n{python_code}\n```{context}"
        
        # Call LLM
        response = call_gemini(prompt, temperature=0.1, max_tokens=4096)
        
        # Parse response
        try:
            json_str = response.strip()
            if '```json' in json_str:
                json_str = json_str.split('```json')[1].split('```')[0].strip()
            elif '```' in json_str:
                json_str = json_str.split('```')[1].split('```')[0].strip()
            
            result = json.loads(json_str)
            
            # Add metadata
            result['file'] = str(py_path)
            result['python_code'] = python_code
            result['total_count'] = len(result.get('parameters', []))
            result['extraction_method'] = 'ai'
            
            self.last_extraction = result
            return result
            
        except json.JSONDecodeError as e:
            return {
                'error': True,
                'message': f'Failed to parse AI response: {str(e)}',
                'raw_response': response,
                'file': str(py_path),
                'parameters': [],
                'total_count': 0
            }
    
    def extract_with_fallback(self, json_file_path: str, py_file_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract parameters with fallback strategy:
        1. Try AI extraction from JSON (most accurate)
        2. If fails, try AI extraction from Python
        3. If fails, use rule-based extraction
        """
        
        # Try AI from JSON first
        try:
            result = self.extract_from_json(json_file_path)
            if not result.get('error') and result.get('total_count', 0) > 0:
                return result
        except Exception as e:
            print(f"AI JSON extraction failed: {e}")
        
        # Try AI from Python if available
        if py_file_path:
            try:
                result = self.extract_from_python(py_file_path, json_file_path)
                if not result.get('error') and result.get('total_count', 0) > 0:
                    return result
            except Exception as e:
                print(f"AI Python extraction failed: {e}")
        
        # Fallback to rule-based extraction
        try:
            from services.intelligent_parameter_extractor import IntelligentParameterExtractor
            extractor = IntelligentParameterExtractor()
            result = extractor.extract_from_json(json_file_path)
            result['extraction_method'] = 'rule_based_fallback'
            return result
        except Exception as e:
            return {
                'error': True,
                'message': f'All extraction methods failed: {str(e)}',
                'parameters': [],
                'total_count': 0
            }
    
    def generate_markdown(self, params_data: Dict[str, Any]) -> str:
        """Generate markdown representation of parameters"""
        
        if params_data.get('error'):
            return f"# Parameter Extraction Failed\n\n{params_data.get('message', 'Unknown error')}"
        
        md_lines = [
            "# Extracted Parameters",
            "",
            f"**Shape:** {params_data.get('shape_type', 'Unknown')}",
            f"**Design Intent:** {params_data.get('design_intent', 'N/A')}",
            f"**Total Parameters:** {params_data.get('total_count', 0)}",
            f"**Extraction Method:** {params_data.get('extraction_method', 'unknown').replace('_', ' ').title()}",
            f"**Units:** {params_data.get('units', 'mm')}",
            "",
            "---",
            ""
        ]
        
        parameters = params_data.get('parameters', [])
        
        if not parameters:
            md_lines.append("*No parameters extracted.*")
            return "\n".join(md_lines)
        
        # Group by priority
        high_priority = [p for p in parameters if p.get('priority') == 'high']
        medium_priority = [p for p in parameters if p.get('priority') == 'medium']
        low_priority = [p for p in parameters if p.get('priority') == 'low']
        other = [p for p in parameters if p.get('priority') not in ['high', 'medium', 'low']]
        
        if high_priority:
            md_lines.append("## 🎯 Primary Dimensions")
            md_lines.append("")
            for param in high_priority:
                md_lines.extend(self._format_parameter(param))
        
        if medium_priority:
            md_lines.append("## 📐 Secondary Parameters")
            md_lines.append("")
            for param in medium_priority:
                md_lines.extend(self._format_parameter(param))
        
        if low_priority:
            md_lines.append("## 🔧 Fine-Tuning")
            md_lines.append("")
            for param in low_priority:
                md_lines.extend(self._format_parameter(param))
        
        if other:
            md_lines.append("## 📋 Other Parameters")
            md_lines.append("")
            for param in other:
                md_lines.extend(self._format_parameter(param))
        
        return "\n".join(md_lines)
    
    def _format_parameter(self, param: Dict) -> List[str]:
        """Format a single parameter for markdown"""
        
        lines = [
            f"### {param.get('description', param.get('name', 'Parameter'))}",
            f"- **Name:** `{param.get('name', 'unknown')}`",
            f"- **Value:** {param.get('value', 0)} {param.get('unit', '')}",
            f"- **Type:** {param.get('type', 'float')}",
            f"- **Range:** {param.get('min', 0)} - {param.get('max', 100)} {param.get('unit', '')}",
            f"- **Category:** {param.get('category', 'unknown')}",
            ""
        ]
        
        return lines
