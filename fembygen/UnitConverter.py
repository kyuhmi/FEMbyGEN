import pint
from typing import Dict, Any

class UnitConverter:
    """
    A class to convert material properties between different unit systems using pint.

    Specifically designed for FreeCAD-Calculix integration, converting from various units
    to the standard unit system:
    - Length: mm
    - Mass: t (tonne)
    - Time: s (second)
    - Temperature: K (kelvin)

    This leads to derived units:
    - Force: N
    - Pressure: N/mm² (MPa)
    - Density: t/mm³
    - Thermal conductivity: t·mm/K/s³ (equivalent to kW/mm/K)
    - Specific Heat: mm²/s²/K (equivalent to kJ/t/K)
    """

    def __init__(self):
        # Initialize the unit registry
        self.ureg = pint.UnitRegistry()

        # Define the target unit system (Calculix/FreeCAD standard)
        self.target_units = {
            'Density': self.ureg.t / self.ureg.mm**3,
            'PoissonRatio': self.ureg.dimensionless,
            'SpecificHeat': self.ureg.mm**2 / (self.ureg.s**2 * self.ureg.K),
            'ThermalConductivity': self.ureg.t * self.ureg.mm / (self.ureg.s**3 * self.ureg.K),
            'ThermalExpansionCoefficient': 1 / self.ureg.K,
            'UltimateTensileStrength': self.ureg.kg / (self.ureg.mm * self.ureg.s**2),
            'YieldStrength': self.ureg.kg / (self.ureg.mm * self.ureg.s**2),
            'YoungsModulus': self.ureg.kg / (self.ureg.mm * self.ureg.s**2),
            'Thickness': self.ureg.mm
        }

    def preprocess_string(self, value_str: str) -> str:
        return value_str.replace(',', '.')

    def parse_quantity(self, value_str: str) -> pint.Quantity:
        """Parse a string representation of a quantity into a pint Quantity."""
        try:
            # try parse with units
            value_part, unit_part = self.preprocess_string(value_str).split(' ', 1)
            return float(value_part) * self.ureg(unit_part)
        except (pint.errors.UndefinedUnitError, ValueError) as e:
            try:
                # If the value is numeric without units, return as dimensionless
                return float(value_str) * self.ureg.dimensionless
            except ValueError:
                raise ValueError(f"Could not parse quantity: {value_str}") from e

    def convert_property(self, property_name: str, value: str) -> pint.Quantity:
        """
        Convert a material property from its input units to the target unit system.

        Args:
            property_name: Name of the material property (e.g., 'Density')
            value: String representation of the property value with units (e.g., '1.24e-06 kg/mm^3')

        Returns:
            pint.Quantity: The converted value in the target unit system
        """
        if property_name not in self.target_units:
            return self.parse_quantity(value)

        # Parse the input quantity
        quantity = self.parse_quantity(value)

        # Convert to the target unit system
        try:
            converted = quantity.to(self.target_units[property_name])
            return converted
        except pint.errors.DimensionalityError as e:
            raise ValueError(
                f"Cannot convert {property_name} from {quantity.units} to "
                f"{self.target_units[property_name]}: incompatible dimensions"
            ) from e

    def convert_material_dict(
            self,
            material_dict: Dict[str, Any],
            include_magnitudes_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Convert all material properties in a dictionary to the target unit system.

        Args:
            material_dict: Dictionary of material properties
            include_magnitudes_only: If True, output will include a '_magnitude' key with just the numeric value

        Returns:
            Dict: Copy of the input dictionary with converted values
        """
        result = material_dict.copy()
        converted_values = {}

        for key, value in material_dict.items():
            # Skip non-numeric properties
            if not isinstance(value, (str, int, float)):
                continue

            # Skip properties that don't have units in their string representation
            if isinstance(value, str) and not any(char.isdigit() for char in value):
                continue

            try:
                # Convert the property
                if isinstance(value, (int, float)):
                    value_str = str(value)
                else:
                    value_str = value

                converted = self.convert_property(key, value_str)

                # Store the original string
                converted_values[f"{key}_original"] = value

                # Store the full pint quantity as string
                converted_values[key] = str(converted)

                # Optionally store just the magnitude
                if include_magnitudes_only:
                    converted_values[f"{key}_magnitude"] = converted.magnitude

            except (ValueError, pint.errors.UndefinedUnitError) as e:
                # Keep the original value if conversion fails
                print(f"Warning: Could not convert {key}: {e}")
                converted_values[key] = value

        result.update(converted_values)
        return result

    def get_magnitude_for_ccx(self, property_name: str, value: str) -> float:
        """
        Convert a property and return just the magnitude for writing to a Calculix input file.

        Args:
            property_name: Name of the material property
            value: String representation of the value with units

        Returns:
            float: The magnitude in the target unit system
        """
        converted = self.convert_property(property_name, value)
        return converted.magnitude
