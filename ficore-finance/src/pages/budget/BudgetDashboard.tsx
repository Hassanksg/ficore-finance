import React, { useEffect, useState } from 'react';
import { IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonCard, IonCardHeader, IonCardTitle, IonCardContent, IonGrid, IonRow, IonCol, IonList, IonItem, IonLabel, IonButton, IonAlert } from '@ionic/react';
import { PieChart } from 'react-minimal-pie-chart'; // Or use Chart.js as per structure
import ToolHeader from '../../components/ToolHeader';
import { t } from '../../utils/translations';
import { getBudgetDashboard } from '../../utils/api'; // GET /budget/dashboard

const BudgetDashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await getBudgetDashboard();
        setDashboardData(data);
        setLoading(false);
      } catch (err) {
        setError(t('budget_fetch_error', { defaultValue: 'Error fetching dashboard data' }));
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <IonContent><p>Loading...</p></IonContent>;
  if (error) return <IonContent><p>{error}</p></IonContent>;

  const latestBudget = dashboardData.latest_budget || {};
  const categories = dashboardData.categories || [];
  const budgets = dashboardData.budgets || [];
  const insights = dashboardData.insights || [];
  const tips = dashboardData.tips || [];

  return (
    <IonPage>
      <IonHeader>
        <IonToolbar>
          <IonTitle>{t('budget_dashboard', { defaultValue: 'Budget Dashboard' })}</IonTitle>
        </IonToolbar>
      </IonHeader>
      <IonContent fullscreen>
        <ToolHeader 
          toolName="budget_dashboard" 
          toolIcon="bi-chart-pie" 
          subtitle={t('budget_dashboard_description', { defaultValue: 'View your financial overview, insights, and budget performance' })} 
        />

        {latestBudget.id ? (
          <>
            <IonGrid>
              <IonRow>
                <IonCol size="4">
                  <IonCard>
                    <IonCardHeader>
                      <IonCardTitle>{t('budget_income', { defaultValue: 'Income' })}</IonCardTitle>
                    </IonCardHeader>
                    <IonCardContent>{latestBudget.income}</IonCardContent>
                  </IonCard>
                </IonCol>
                {/* Similar for expenses, surplus_deficit */}
              </IonRow>
            </IonGrid>

            {categories.length > 0 && (
              <IonCard>
                <IonCardHeader>
                  <IonCardTitle>{t('budget_expense_breakdown', { defaultValue: 'Expense Breakdown' })}</IonCardTitle>
                </IonCardHeader>
                <IonCardContent>
                  <PieChart data={categories.map(cat => ({ title: cat.label, value: cat.value, color: cat.color }))} />
                </IonCardContent>
              </IonCard>
            )}

            {/* Budget History Table */}
            <IonCard>
              <IonCardHeader>
                <IonCardTitle>{t('budget_history', { defaultValue: 'Budget History' })}</IonCardTitle>
              </IonCardHeader>
              <IonCardContent>
                <IonList>
                  {budgets.map((budget: any) => (
                    <IonItem key={budget.id}>
                      <IonLabel>{budget.created_at} - Income: {budget.income}, Expenses: {budget.total_expenses}</IonLabel>
                    </IonItem>
                  ))}
                </IonList>
              </IonCardContent>
            </IonCard>

            {/* Insights and Tips Lists */}
          </>
        ) : (
          <IonCard>
            <IonCardContent>
              <p>{t('budget_no_data', { defaultValue: 'No budget data available' })}</p>
              <IonButton routerLink="/budget/new">{t('budget_create_first_budget', { defaultValue: 'Create Your First Budget' })}</IonButton>
            </IonCardContent>
          </IonCard>
        )}
      </IonContent>
    </IonPage>
  );
};

export default BudgetDashboard;