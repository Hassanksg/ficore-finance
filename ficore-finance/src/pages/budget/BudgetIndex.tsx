import React from 'react';
import { IonPage, IonHeader, IonToolbar, IonTitle, IonContent, IonCard, IonCardHeader, IonCardTitle, IonCardSubtitle, IonCardContent, IonButton, IonIcon, IonList, IonItem, IonLabel } from '@ionic/react';
import { calculatorOutline } from 'ionicons/icons';
import ToolHeader from '../../components/ToolHeader';
import { t } from '../../utils/translations'; // Assuming a translation hook or function

const BudgetIndex: React.FC = () => {
  return (
    <IonPage>
      <IonHeader>
        <IonToolbar>
          <IonTitle>{t('budget_title', { defaultValue: 'Budget Planner' })}</IonTitle>
        </IonToolbar>
      </IonHeader>
      <IonContent fullscreen>
        <ToolHeader 
          toolName="budget_title" 
          toolIcon="bi-calculator" // Adapted to bootstrap icon, or use ion-icon
          subtitle={t('budget_subtitle', { defaultValue: 'Plan and manage your finances effectively' })} 
        />

        <IonCard>
          <IonCardHeader>
            <IonCardTitle>{t('budget_create_budget', { defaultValue: 'Create New Budget' })}</IonCardTitle>
            <IonCardSubtitle>{t('budget_create_description', { defaultValue: 'Plan your monthly income and expenses to achieve your financial goals' })}</IonCardSubtitle>
          </IonCardHeader>
          <IonCardContent>
            <IonButton routerLink="/budget/new" fill="solid" expand="block">
              {t('budget_get_started', { defaultValue: 'Get Started' })}
            </IonButton>
          </IonCardContent>
        </IonCard>

        <IonCard>
          <IonCardHeader>
            <IonCardTitle>{t('budget_dashboard', { defaultValue: 'Budget Dashboard' })}</IonCardTitle>
            <IonCardSubtitle>{t('budget_dashboard_description', { defaultValue: 'View your financial overview, insights, and budget performance' })}</IonCardSubtitle>
          </IonCardHeader>
          <IonCardContent>
            <IonButton routerLink="/budget/dashboard" fill="solid" expand="block">
              {t('budget_view_dashboard', { defaultValue: 'View Dashboard' })}
            </IonButton>
          </IonCardContent>
        </IonCard>

        <IonCard>
          <IonCardHeader>
            <IonCardTitle>{t('budget_manage_budgets', { defaultValue: 'Manage Budgets' })}</IonCardTitle>
            <IonCardSubtitle>{t('budget_manage_description', { defaultValue: 'Review, edit, and organize your existing budgets' })}</IonCardSubtitle>
          </IonCardHeader>
          <IonCardContent>
            <IonButton routerLink="/budget/manage" fill="solid" expand="block">
              {t('budget_manage_now', { defaultValue: 'Manage Now' })}
            </IonButton>
          </IonCardContent>
        </IonCard>

        <IonCard>
          <IonCardHeader>
            <IonCardTitle>{t('budget_quick_tips', { defaultValue: 'Quick Tips' })}</IonCardTitle>
          </IonCardHeader>
          <IonCardContent>
            <IonList>
              <IonItem>
                <IonLabel>{t('budget_tip_track_expenses', { defaultValue: 'Track your expenses daily to stay within budget' })}</IonLabel>
              </IonItem>
              <IonItem>
                <IonLabel>{t('budget_tip_ajo_savings', { defaultValue: 'Contribute to ajo savings for financial discipline' })}</IonLabel>
              </IonItem>
              <IonItem>
                <IonLabel>{t('budget_tip_data_subscriptions', { defaultValue: 'Optimize data subscriptions to reduce costs' })}</IonLabel>
              </IonItem>
              <IonItem>
                <IonLabel>{t('budget_tip_plan_dependents', { defaultValue: 'Plan for dependents\' expenses in advance' })}</IonLabel>
              </IonItem>
            </IonList>
          </IonCardContent>
        </IonCard>
      </IonContent>
    </IonPage>
  );
};

export default BudgetIndex;