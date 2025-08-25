import React, { useState } from 'react';
import { IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonCard, IonCardHeader, IonCardTitle, IonCardSubtitle, IonCardContent, IonButton, IonInput, IonItem, IonLabel, IonList, IonSelect, IonSelectOption, IonAlert } from '@ionic/react';
import ToolHeader from '../../components/ToolHeader';
import { t } from '../../utils/translations';
import { useHistory } from 'react-router-dom';
import { postBudget } from '../../utils/api'; // Assuming API wrapper for POST /budget/new

interface CustomCategory {
  name: string;
  amount: number;
}

const BudgetNew: React.FC = () => {
  const history = useHistory();
  const [formData, setFormData] = useState({
    income: 0,
    housing: 0,
    food: 0,
    transport: 0,
    dependents: 0,
    miscellaneous: 0,
    others: 0,
    savings_goal: 0,
    custom_categories: [] as CustomCategory[],
  });
  const [errors, setErrors] = useState<{ [key: string]: string[] }>({});
  const [showAlert, setShowAlert] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');

  const handleInputChange = (e: CustomEvent) => {
    const { name, value } = e.target as HTMLInputElement;
    setFormData(prev => ({ ...prev, [name]: parseFloat(value) || 0 }));
  };

  const addCustomCategory = () => {
    setFormData(prev => ({
      ...prev,
      custom_categories: [...prev.custom_categories, { name: '', amount: 0 }],
    }));
  };

  const handleCustomCategoryChange = (index: number, field: 'name' | 'amount', value: string) => {
    const updated = [...formData.custom_categories];
    updated[index][field] = field === 'amount' ? parseFloat(value) || 0 : value;
    setFormData(prev => ({ ...prev, custom_categories: updated }));
  };

  const removeCustomCategory = (index: number) => {
    const updated = formData.custom_categories.filter((_, i) => i !== index);
    setFormData(prev => ({ ...prev, custom_categories: updated }));
  };

  const validateForm = () => {
    const newErrors: { [key: string]: string[] } = {};
    if (formData.income <= 0) newErrors.income = [t('budget_income_required', { defaultValue: 'Income is required and must be positive' })];
    // Add more validations mirroring WTForms: NumberRange(min=0, max=10000000000), etc.
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;
    try {
      const response = await postBudget(formData); // POST to /budget/new
      if (response.success) {
        setAlertMessage(t('budget_created_success', { defaultValue: 'Budget created successfully!' }));
        setShowAlert(true);
        history.push('/budget/dashboard');
      } else {
        setErrors(response.errors || {});
      }
    } catch (error) {
      setAlertMessage(t('budget_create_error', { defaultValue: 'Error creating budget. Please try again.' }));
      setShowAlert(true);
    }
  };

  return (
    <IonPage>
      <IonHeader>
        <IonToolbar>
          <IonTitle>{t('budget_create_budget', { defaultValue: 'Create Budget' })}</IonTitle>
        </IonToolbar>
      </IonHeader>
      <IonContent fullscreen>
        <ToolHeader 
          toolName="budget_create_budget" 
          toolIcon="bi-plus-circle" 
          subtitle={t('budget_create_description', { defaultValue: 'Plan your monthly income and expenses to achieve your financial goals' })} 
        />

        <IonCard>
          <IonCardContent>
            <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
              {/* Monthly Income */}
              <IonItem>
                <IonLabel position="stacked">{t('budget_monthly_income', { defaultValue: 'Monthly Income' })}</IonLabel>
                <IonInput name="income" type="number" value={formData.income} onIonChange={handleInputChange} required />
                {errors.income && <IonLabel color="danger">{errors.income[0]}</IonLabel>}
              </IonItem>

              {/* Expenses Sections */}
              <IonList>
                <IonItem>
                  <IonLabel position="stacked">{t('budget_housing_rent', { defaultValue: 'Housing/Rent' })}</IonLabel>
                  <IonInput name="housing" type="number" value={formData.housing} onIonChange={handleInputChange} required />
                </IonItem>
                {/* Similarly for food, transport, dependents, miscellaneous, others */}
              </IonList>

              {/* Custom Categories */}
              <IonItem>
                <IonLabel>{t('budget_custom_categories', { defaultValue: 'Custom Categories' })}</IonLabel>
              </IonItem>
              {formData.custom_categories.map((cat, index) => (
                <IonItem key={index}>
                  <IonInput 
                    placeholder={t('budget_custom_category_name', { defaultValue: 'Category Name' })} 
                    value={cat.name} 
                    onIonChange={(e) => handleCustomCategoryChange(index, 'name', e.detail.value!)} 
                  />
                  <IonInput 
                    type="number" 
                    placeholder={t('budget_custom_category_amount', { defaultValue: 'Amount' })} 
                    value={cat.amount} 
                    onIonChange={(e) => handleCustomCategoryChange(index, 'amount', e.detail.value!)} 
                  />
                  <IonButton slot="end" onClick={() => removeCustomCategory(index)} color="danger">
                    {t('general_remove', { defaultValue: 'Remove' })}
                  </IonButton>
                </IonItem>
              ))}
              <IonButton onClick={addCustomCategory} expand="block">
                {t('budget_add_custom_category', { defaultValue: 'Add Custom Category' })}
              </IonButton>

              {/* Savings Goal */}
              <IonItem>
                <IonLabel position="stacked">{t('budget_savings_goal', { defaultValue: 'Monthly Savings Goal' })}</IonLabel>
                <IonInput name="savings_goal" type="number" value={formData.savings_goal} onIonChange={handleInputChange} required />
              </IonItem>

              <IonButton type="submit" expand="block">{t('budget_calculate_budget', { defaultValue: 'Calculate Budget' })}</IonButton>
            </form>
          </IonCardContent>
        </IonCard>

        {/* Tips and Recent Activities sections similar to template */}

        <IonAlert
          isOpen={showAlert}
          onDidDismiss={() => setShowAlert(false)}
          message={alertMessage}
          buttons={['OK']}
        />
      </IonContent>
    </IonPage>
  );
};

export default BudgetNew;