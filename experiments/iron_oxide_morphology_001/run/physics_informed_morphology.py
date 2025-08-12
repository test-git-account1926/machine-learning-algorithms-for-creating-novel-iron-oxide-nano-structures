#!/usr/bin/env python3
"""
Physics-Informed ML for Iron Oxide Morphology Prediction
Implementation of the exp_iron_oxide_001 experiment
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import json
import os
from datetime import datetime

# Physical constants
R = 8.314  # J/(mol*K)
NA = 6.022e23  # Avogadro's number

class PhysicsFeatureEngine:
    """Calculate physics-informed features for iron oxide synthesis"""
    
    def __init__(self):
        # Thermodynamic data for Fe2O3 polymorphs (simplified)
        self.formation_energies = {
            'alpha_fe2o3': -824.2,  # kJ/mol
            'gamma_fe2o3': -806.7,  # kJ/mol
            'beta_fe2o3': -812.1    # kJ/mol
        }
        
        # Surface energies (J/m²)
        self.surface_energies = {
            'nanorods': 1.2,
            'cubes': 1.0, 
            'spheres': 0.8,
            'flowers': 1.5
        }
    
    def calculate_gibbs_energy(self, temperature, ph):
        """Calculate Gibbs free energy for Fe2O3 formation"""
        T = temperature + 273.15  # Convert to Kelvin
        
        # Simplified thermodynamic calculation
        delta_g_formation = self.formation_energies['alpha_fe2o3']
        
        # pH effect on formation (simplified)
        ph_correction = -R * T * np.log10(14 - ph) / 1000  # kJ/mol
        
        return delta_g_formation + ph_correction
    
    def calculate_nucleation_barrier(self, temperature, concentration):
        """Calculate nucleation barrier using classical nucleation theory"""
        T = temperature + 273.15
        
        # Simplified nucleation barrier calculation
        # Assuming surface tension ~0.1 J/m²
        gamma = 0.1  # J/m²
        k_b = 1.38e-23  # J/K
        
        # Critical radius (simplified)
        r_critical = 2 * gamma / (k_b * T * np.log(concentration/0.01))
        
        # Nucleation barrier
        barrier = (16 * np.pi * gamma**3) / (3 * (k_b * T)**2 * (np.log(concentration/0.01))**2)
        
        return barrier
    
    def calculate_surface_energy_ratio(self, temperature, ph):
        """Calculate relative surface energy favoring different morphologies"""
        # Temperature effect on surface energy (simplified)
        temp_factor = 1 - (temperature - 100) / 1000
        ph_factor = 1 + abs(ph - 7) / 10
        
        ratios = {}
        for morph, energy in self.surface_energies.items():
            ratios[f'surface_ratio_{morph}'] = energy * temp_factor * ph_factor
        
        return ratios

def generate_synthetic_dataset(n_samples=1000):
    """Generate synthetic hydrothermal synthesis dataset"""
    np.random.seed(42)  # For reproducibility
    
    # Generate synthesis parameters
    data = {
        'temperature': np.random.uniform(80, 220, n_samples),
        'ph': np.random.uniform(2, 12, n_samples), 
        'time_hours': np.random.uniform(1, 24, n_samples),
        'concentration': np.random.uniform(0.01, 0.5, n_samples),
        'surfactant': np.random.choice(['none', 'peg', 'ctab', 'sds'], n_samples)
    }
    
    # Generate morphology labels based on heuristic rules
    morphologies = []
    for i in range(n_samples):
        temp = data['temperature'][i]
        ph = data['ph'][i]
        time = data['time_hours'][i]
        conc = data['concentration'][i]
        
        # Heuristic rules for morphology (simulating real physics)
        if temp > 180 and ph < 4:
            morph = 'nanorods'
        elif temp < 120 and ph > 10:
            morph = 'cubes' 
        elif conc < 0.1 and time > 12:
            morph = 'spheres'
        elif ph > 8 and time < 6:
            morph = 'flowers'
        else:
            # Random assignment for mixed conditions
            morph = np.random.choice(['nanorods', 'cubes', 'spheres', 'flowers'])
        
        morphologies.append(morph)
    
    data['morphology'] = morphologies
    
    return pd.DataFrame(data)

def add_physics_features(df):
    """Add physics-informed features to dataset"""
    physics = PhysicsFeatureEngine()
    
    # Calculate physics features
    df['gibbs_energy'] = df.apply(lambda row: physics.calculate_gibbs_energy(
        row['temperature'], row['ph']), axis=1)
    
    df['nucleation_barrier'] = df.apply(lambda row: physics.calculate_nucleation_barrier(
        row['temperature'], row['concentration']), axis=1)
    
    # Add surface energy ratios
    surface_ratios = df.apply(lambda row: physics.calculate_surface_energy_ratio(
        row['temperature'], row['ph']), axis=1)
    
    for key in ['surface_ratio_nanorods', 'surface_ratio_cubes', 
                'surface_ratio_spheres', 'surface_ratio_flowers']:
        df[key] = [ratio[key] for ratio in surface_ratios]
    
    return df

def run_experiment():
    """Main experiment execution"""
    print("Starting Physics-Informed ML for Iron Oxide Morphology Prediction")
    print("=" * 70)
    
    # Generate synthetic dataset
    print("1. Generating synthetic dataset...")
    df = generate_synthetic_dataset(1000)
    print(f"   Generated {len(df)} synthesis conditions")
    print(f"   Morphology distribution: {df['morphology'].value_counts().to_dict()}")
    
    # Add physics features
    print("\n2. Adding physics-informed features...")
    df = add_physics_features(df)
    
    # One-hot encode categorical features
    df_encoded = pd.get_dummies(df, columns=['surfactant'])
    
    # Separate features and target
    feature_cols = [col for col in df_encoded.columns if col != 'morphology']
    X = df_encoded[feature_cols]
    y = df_encoded['morphology']
    
    print(f"   Total features: {len(feature_cols)}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Train models
    print("\n3. Training models...")
    
    # Empirical features only (baseline)
    empirical_features = ['temperature', 'ph', 'time_hours', 'concentration'] + \
                        [col for col in X.columns if 'surfactant_' in col]
    X_empirical = X[empirical_features]
    X_emp_train, X_emp_test = X_empirical.iloc[X_train.index], X_empirical.iloc[X_test.index]
    
    model_empirical = RandomForestClassifier(n_estimators=100, random_state=42)
    model_empirical.fit(X_emp_train, y_train)
    emp_score = model_empirical.score(X_emp_test, y_test)
    
    # Physics-enhanced model
    model_physics = RandomForestClassifier(n_estimators=100, random_state=42)
    model_physics.fit(X_train, y_train)
    physics_score = model_physics.score(X_test, y_test)
    
    print(f"   Empirical-only accuracy: {emp_score:.3f}")
    print(f"   Physics-enhanced accuracy: {physics_score:.3f}")
    print(f"   Improvement: {physics_score - emp_score:.3f}")
    
    # Feature importance analysis
    print("\n4. Feature importance analysis...")
    importances = model_physics.feature_importances_
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': importances
    }).sort_values('importance', ascending=False)
    
    print("   Top 10 most important features:")
    for i, (_, row) in enumerate(feature_importance.head(10).iterrows()):
        print(f"   {i+1:2d}. {row['feature']:25s} {row['importance']:.3f}")
    
    # Detailed evaluation on test set
    print("\n5. Detailed evaluation...")
    y_pred = model_physics.predict(X_test)
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Save results
    results = {
        'experiment_id': 'exp_iron_oxide_001',
        'experiment_name': 'Physics-Informed ML for Iron Oxide Morphology Prediction',
        'date': datetime.now().isoformat(),
        'dataset_size': len(df),
        'features_total': len(feature_cols),
        'empirical_accuracy': float(emp_score),
        'physics_enhanced_accuracy': float(physics_score),
        'improvement': float(physics_score - emp_score),
        'target_achieved': physics_score > 0.85,
        'morphology_distribution': df['morphology'].value_counts().to_dict(),
        'top_features': feature_importance.head(10).to_dict('records'),
        'classification_report': classification_report(y_test, y_pred, output_dict=True)
    }
    
    # Save to data folder
    os.makedirs('../../data/iron_oxide_synthesis', exist_ok=True)
    
    with open('../../data/iron_oxide_synthesis/experiment_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    # Save dataset
    df.to_csv('../../data/iron_oxide_synthesis/synthetic_dataset.csv', index=False)
    
    print(f"\n6. Results summary:")
    print(f"   Target accuracy (>85%): {'✓' if results['target_achieved'] else '✗'}")
    print(f"   Physics enhancement: +{results['improvement']:.1%}")
    print(f"   Best feature: {results['top_features'][0]['feature']}")
    
    return results

if __name__ == "__main__":
    results = run_experiment()