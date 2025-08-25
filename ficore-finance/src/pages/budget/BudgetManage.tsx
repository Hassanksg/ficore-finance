import React, { useEffect, useState } from 'react';
import { IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonCard, IonCardHeader, IonCardTitle, IonCardContent, IonButton, IonList, IonItem, IonLabel, IonAccordionGroup, IonAccordion, IonAlert } from '@ionic/react';
import ToolHeader from '../../components/ToolHeader';
import { t } from '../../utils/translations';
import { getBudgets, deleteBudget, exportBudgetPdf } from '../../utils/api'; // GET /budget/manage, POST /budget/delete_budget, GET /budget/export

const BudgetManage: React.FC = () => {
  const [budgets, setBudgets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAlert, setShowAlert] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');

  useEffect(() => {
    const fetchBudgets = async () => {
      try {
        const data = await getBudgets();
        setBudgets(data.budgets || []);
        setLoading(false);
      } catch (err) {
        setAlertMessage(t('budget_fetch_error', { defaultValue: 'Error fetching budgets' }));
        setShowAlert(true);
        setLoading(false);
      }
    };
    fetchBudgets();
  }, []);

  const handleDelete = async (budgetId: string) => {
    try {
      const response = await deleteBudget(budgetId);
      if (response.success) {
        setBudgets(prev => prev.filter(b => b.id !== budgetId));
        setAlertMessage(t('budget_deleted', { defaultValue: 'Budget deleted successfully!' }));
        setShowAlert(true);
      }
    } catch (err) {
      setAlertMessage(t('budget_delete_error', { defaultValue: 'Error deleting budget' }));
      setShowAlert(true);
    }
  };

  const handleExportPdf = async (type: 'single' | 'history', budgetId?: string) => {
    try {
      const pdfBlob = await exportBudgetPdf(type, budgetId);
      // Use Capacitor Filesystem to save/download PDF
      // Assuming native.ts has a downloadPdf function
    } catch (err) {
      setAlertMessage(t('budget_pdf_error', { defaultValue: 'Error generating PDF' }));
      setShowAlert(true);
    }
  };

  if (loading) return <IonContent><p>Loading...</p></IonContent>;

  return (
    <IonPage>
      <IonHeader>
        <IonToolbar>
          <IonTitle>{t('budget_manage_budgets', { defaultValue: 'Manage Budgets' })}</IonTitle>
        </IonToolbar>
      </IonHeader>
      <IonContent fullscreen>
        <ToolHeader 
          toolName="budget_manage_budgets" 
          toolIcon="bi-edit" 
          subtitle={t('budget_manage_description', { defaultValue: 'Review, edit, and organize your existing budgets' })} 
        />

        {budgets.length > 0 ? (
          <>
            <IonCard>
              <IonCardHeader>
                <IonCardTitle>{t('budget_your_budgets', { defaultValue: 'Your Budgets' })} ({budgets.length})</IonCardTitle>
              </IonCardHeader>
              <IonCardContent>
                <IonButton routerLink="/budget/new">{t('budget_create_budget', { defaultValue: 'Create Budget' })}</IonButton>
              </IonCardContent>
            </IonCard>

            <IonAccordionGroup>
              {budgets.map((budget, index) => (
                <IonAccordion key={budget.id} value={budget.id}>
                  <IonItem slot="header">
                    <IonLabel>{t('budget_budget', { defaultValue: 'Budget' })} #{index + 1} - {budget.created_at}</IonLabel>
                  </IonItem>
                  <div slot="content">
                    {/* Display budget details, custom categories, actions: export, delete */}
                    <IonButton onClick={() => handleExportPdf('single', budget.id)}>{t('budget_export', { defaultValue: 'Export' })}</IonButton>
                    <IonButton color="danger" onClick={() => handleDelete(budget.id)}>{t('general_delete', { defaultValue: 'Delete' })}</IonButton>
                  </div>
                </IonAccordion>
              ))}
            </IonAccordionGroup>
          </>
        ) : (
          <IonCard>
            <IonCardContent>
              <p>{t('budget_no_budgets_empty_state', { defaultValue: 'No budgets created yet' })}</p>
              <IonButton routerLink="/budget/new">{t('budget_create_first_budget', { defaultValue: 'Create Your First Budget' })}</IonButton>
            </IonCardContent>
          </IonCard>
        )}

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

export default BudgetManage;