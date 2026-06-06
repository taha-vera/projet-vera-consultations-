use std::collections::HashMap;
use std::time::{SystemTime,UNIX_EPOCH};
pub const EPSILON_MAX:f64=1.0;
pub const LAMBDA:f64=8.02e-6;
pub const OMEGA:f64=0.7;
pub fn now_secs()->f64{SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs_f64()}
#[derive(Debug,Clone)]
pub struct ContributorState{pub contributor_id:String,pub epsilon_restant:f64,pub dernier_calcul:f64,pub solde_financier:f64,pub nb_requetes:usize}
impl ContributorState{
    pub fn new(id:&str)->Self{Self{contributor_id:id.to_string(),epsilon_restant:EPSILON_MAX,dernier_calcul:now_secs(),solde_financier:0.0,nb_requetes:0}}
    pub fn epsilon_actuel(&self,t:Option<f64>)->f64{let now=t.unwrap_or_else(now_secs);let dt=(now-self.dernier_calcul).max(0.0);(EPSILON_MAX-(EPSILON_MAX-self.epsilon_restant)*(-LAMBDA*dt).exp()).clamp(0.0,EPSILON_MAX)}
}
#[derive(Debug,Clone,PartialEq)]
pub enum RechargeError{BudgetInsuffisant{epsilon_actuel:f64,delta_epsilon:f64},ValeurInvalide(f64),DeltaEpsilonInvalide(f64)}
#[derive(Debug,Clone)]
pub struct ResultatRequete{pub contributor_id:String,pub epsilon_avant:f64,pub epsilon_apres:f64,pub gain_contributeur:f64,pub timestamp:f64}
pub struct RechargeTracker{pub lambda:f64,pub omega:f64,states:HashMap<String,ContributorState>,audit_log:Vec<ResultatRequete>}
impl RechargeTracker{
    pub fn new(lambda:f64,omega:f64)->Self{Self{lambda,omega,states:HashMap::new(),audit_log:Vec::new()}}
    pub fn register(&mut self,id:&str){self.states.entry(id.to_string()).or_insert_with(||ContributorState::new(id));}
    pub fn traiter_requete(&mut self,id:&str,de:f64,val:f64,t:Option<f64>)->Result<ResultatRequete,RechargeError>{
        if !val.is_finite()||val<0.0{return Err(RechargeError::ValeurInvalide(val));}
        if !de.is_finite()||de<=0.0{return Err(RechargeError::DeltaEpsilonInvalide(de));}
        let now=t.unwrap_or_else(now_secs);
        self.register(id);
        let s=self.states.get_mut(id).unwrap();
        let dt=(now-s.dernier_calcul).max(0.0);
        let eps=(EPSILON_MAX-(EPSILON_MAX-s.epsilon_restant)*(-self.lambda*dt).exp()).clamp(0.0,EPSILON_MAX);
        if eps<de{return Err(RechargeError::BudgetInsuffisant{epsilon_actuel:eps,delta_epsilon:de});}
        let gain=val*(de/eps)*self.omega;
        s.epsilon_restant=eps-de;s.dernier_calcul=now;s.solde_financier+=gain;s.nb_requetes+=1;
        let r=ResultatRequete{contributor_id:id.to_string(),epsilon_avant:eps,epsilon_apres:eps-de,gain_contributeur:gain,timestamp:now};
        self.audit_log.push(r.clone());Ok(r)
    }
    pub fn get_state(&self,id:&str)->Option<&ContributorState>{self.states.get(id)}
    pub fn total_redistribue(&self)->f64{self.states.values().map(|s|s.solde_financier).sum()}
    pub fn nb_requetes_total(&self)->usize{self.audit_log.len()}
}
#[cfg(test)]
mod tests{
    use super::*;
    const T0:f64=1_000_000.0;
    fn t()->RechargeTracker{RechargeTracker::new(LAMBDA,OMEGA)}
    #[test]
    fn test_recharge_zero(){let s=ContributorState::new("u1");assert!((s.epsilon_actuel(Some(s.dernier_calcul))-EPSILON_MAX).abs()<1e-12);}
    #[test]
    fn test_recharge_24h(){let mut s=ContributorState::new("u1");s.epsilon_restant=0.5;s.dernier_calcul=T0;let e=s.epsilon_actuel(Some(T0+86400.0));assert!(e>0.5&&e<EPSILON_MAX);println!("eps 24h:{e:.4}");}
    #[test]
    fn test_monotone(){let mut s=ContributorState::new("u1");s.epsilon_restant=0.2;s.dernier_calcul=T0;let v:Vec<f64>=[0.0,3600.0,86400.0,172800.0].iter().map(|&d|s.epsilon_actuel(Some(T0+d))).collect();for i in 0..v.len()-1{assert!(v[i]<=v[i+1]);}}
    #[test]
    fn test_gain_proportionnel(){let mut t=t();let r1=t.traiter_requete("u1",0.1,100.0,Some(T0)).unwrap();let r2=t.traiter_requete("u1",0.1,100.0,Some(T0+1.0)).unwrap();assert!(r2.gain_contributeur>r1.gain_contributeur);println!("r1={:.4} r2={:.4}",r1.gain_contributeur,r2.gain_contributeur);}
    #[test]
    fn test_budget_insuffisant(){let mut t=t();t.traiter_requete("u1",0.9,100.0,Some(T0)).unwrap();assert!(matches!(t.traiter_requete("u1",0.5,100.0,Some(T0+1.0)),Err(RechargeError::BudgetInsuffisant{..})));}
    #[test]
    fn test_debloque_30j(){let mut t=t();t.traiter_requete("u1",0.95,100.0,Some(T0)).unwrap();assert!(t.traiter_requete("u1",0.1,100.0,Some(T0+1.0)).is_err());assert!(t.traiter_requete("u1",0.1,100.0,Some(T0+30.0*86400.0)).is_ok());println!("Debloque 30j OK");}
    #[test]
    fn test_isolation(){let mut t=t();t.traiter_requete("u1",0.9,100.0,Some(T0)).unwrap();assert!(t.traiter_requete("u2",0.9,100.0,Some(T0)).is_ok());}
    #[test]
    fn test_nan_inf(){let mut t=t();assert!(t.traiter_requete("u1",f64::NAN,100.0,Some(T0)).is_err());assert!(t.traiter_requete("u1",0.1,f64::INFINITY,Some(T0)).is_err());}
    #[test]
    fn test_simulation_24h(){
        let mut t=t();
        println!("\n=== Simulation 24h VERA v3.3 ===");
        for h in [0u64,8,16,24]{
            let tc=T0+h as f64*3600.0;
            match t.traiter_requete("u1",0.15,100.0,Some(tc)){
                Ok(r)=>println!("{}h eps:{:.4}->{:.4} gain:{:.4}€",h,r.epsilon_avant,r.epsilon_apres,r.gain_contributeur),
                Err(e)=>println!("{}h BLOQUE:{:?}",h,e),
            }
        }
        println!("Total:{:.4}€",t.total_redistribue());
    }
}
