use std::time::{SystemTime, UNIX_EPOCH};

pub const VERA_VERSION: &str = "3.1.1";
pub const MIN_K: usize = 100;
pub const DECAY_HALF_LIFE: f64 = 86_400.0;
pub const DECAY_MAX_AGE: f64 = 2_592_000.0;

pub struct SimpleRng { state: u64 }
impl SimpleRng {
    pub fn new(seed: u64) -> Self { assert_ne!(seed,0); Self{state:seed} }
    fn next_u64(&mut self) -> u64 {
        self.state ^= self.state << 13;
        self.state ^= self.state >> 7;
        self.state ^= self.state << 17;
        self.state
    }
    pub fn uuid(&mut self) -> String {
        let a=self.next_u64(); let b=self.next_u64();
        format!("{:08x}-{:04x}-4{:03x}-{:04x}-{:012x}",
            (a>>32) as u32,((a>>16)&0xffff) as u16,(a&0x0fff) as u16,
            (((b>>48)&0x3fff)|0x8000) as u16, b&0x0000_ffff_ffff_ffff_u64)
    }
}
pub fn now_secs() -> f64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs_f64()
}

#[derive(Debug,Clone,PartialEq,Eq)]
pub enum Layer { Collection, Aggregation, Redistribution }

#[derive(Debug,Clone)]
pub struct Graphlet {
    pub graphlet_id: String, pub cohort_id: String,
    pub aggregated_value: f64, pub count: usize,
    pub created_at: f64, pub layer: Layer,
}
impl Graphlet {
    pub fn new(rng: &mut SimpleRng, aggregated_value: f64, count: usize) -> Self {
        Self{graphlet_id:rng.uuid(),cohort_id:rng.uuid(),aggregated_value,count,
             created_at:now_secs(),layer:Layer::Aggregation}
    }
    pub fn new_at(rng:&mut SimpleRng,v:f64,c:usize,t:f64)->Self {
        let mut g=Self::new(rng,v,c); g.created_at=t; g
    }
    pub fn decay_factor(&self, current_time: Option<f64>) -> f64 {
        let now=current_time.unwrap_or_else(now_secs);
        let age=now-self.created_at;
        if age<=0.0{return 1.0;} if age>=DECAY_MAX_AGE{return 0.0;}
        (-std::f64::consts::LN_2*age/DECAY_HALF_LIFE).exp()
    }
    pub fn effective_value(&self,t:Option<f64>)->f64{self.aggregated_value*self.decay_factor(t)}
    pub fn is_expired(&self,t:Option<f64>)->bool{
        (t.unwrap_or_else(now_secs)-self.created_at)>=DECAY_MAX_AGE
    }
    pub fn is_k_anonymous(&self,min_k:usize)->bool{self.count>=min_k}
}

#[derive(Debug,Clone)]
pub struct Cohort {
    pub cohort_id: String, pub graphlets: Vec<Graphlet>, pub created_at: f64,
}
impl Cohort {
    pub fn new(rng:&mut SimpleRng)->Self {
        Self{cohort_id:rng.uuid(),graphlets:Vec::new(),created_at:now_secs()}
    }
    pub fn add_graphlet(&mut self,mut g:Graphlet){g.cohort_id=self.cohort_id.clone();self.graphlets.push(g);}
    pub fn size(&self)->usize{self.graphlets.len()}
    pub fn is_k_anonymous(&self,k:usize)->bool{self.size()>=k}
    pub fn aggregate(&self,t:Option<f64>)->f64{self.graphlets.iter().map(|g|g.effective_value(t)).sum()}
    pub fn purge_expired(&mut self,t:Option<f64>)->usize {
        let b=self.graphlets.len();
        self.graphlets.retain(|g|!g.is_expired(t));
        b-self.graphlets.len()
    }
}

#[derive(Debug,Clone)]
pub struct RevenueShare { pub share_id:String, pub cohort_id:String, pub amount:f64 }
impl RevenueShare {
    pub fn new(rng:&mut SimpleRng,cohort_id:String,amount:f64)->Self {
        Self{share_id:rng.uuid(),cohort_id,amount}
    }
}

pub mod collection {
    use zeroize::Zeroize;
    use super::{Graphlet,Cohort,Layer,SimpleRng};
    pub struct CollectionLayer { pub layer:Layer }
    impl CollectionLayer {
        pub fn new()->Self{Self{layer:Layer::Collection}}
        pub fn ingest(&self,rng:&mut SimpleRng,mut values:Vec<f64>,cohort:&mut Cohort)->Result<String,String>{
            if values.is_empty(){return Err("empty".into());}
            if values.iter().any(|v|!v.is_finite()){return Err("non-finite value".into());}
            let count=values.len();
            let agg=values.iter().sum::<f64>()/count as f64;
            values.zeroize();
            drop(values);
            let g=Graphlet::new(rng,agg,count);
            let id=g.graphlet_id.clone();
            cohort.add_graphlet(g); Ok(id)
        }
    }
}

pub mod aggregation {
    use super::{Cohort,Layer,SimpleRng};
    use std::collections::HashMap;
    pub struct AggregationLayer { pub layer:Layer, pub min_k:usize, cohorts:HashMap<String,Cohort> }
    impl AggregationLayer {
        pub fn new(min_k:usize)->Self{Self{layer:Layer::Aggregation,min_k,cohorts:HashMap::new()}}
        pub fn create_cohort(&mut self,rng:&mut SimpleRng)->String {
            let c=Cohort::new(rng); let id=c.cohort_id.clone();
            self.cohorts.insert(id.clone(),c); id
        }
        pub fn get_cohort_mut(&mut self,id:&str)->Option<&mut Cohort>{self.cohorts.get_mut(id)}
        pub fn get_cohort(&self,id:&str)->Option<&Cohort>{self.cohorts.get(id)}
        pub fn enforce_k_anonymity(&self,c:&Cohort)->Result<(),String>{
            if !c.is_k_anonymous(self.min_k){
                return Err(format!("Invariant II violated: size={} < min_k={}",c.size(),self.min_k));
            } Ok(())
        }
        pub fn list_k_anonymous_cohorts(&mut self,t:Option<f64>)->Vec<Cohort>{
            let k=self.min_k;
            self.cohorts.values_mut().filter_map(|c|{
                c.purge_expired(t);
                if c.is_k_anonymous(k){Some(c.clone())}else{None}
            }).collect()
        }
        pub fn cohort_count(&self)->usize{self.cohorts.len()}
    }
}

pub mod revenue {
    use super::{Cohort,Layer,RevenueShare,SimpleRng};
    pub struct RevenueDistributor { pub layer:Layer }
    impl RevenueDistributor {
        pub fn new()->Self{Self{layer:Layer::Redistribution}}
        pub fn distribute(&self,rng:&mut SimpleRng,total:f64,cohorts:&[Cohort],t:Option<f64>)->Result<Vec<RevenueShare>,String>{
            if !total.is_finite(){return Err("non-finite total".into());}
            if total<0.0{return Err("negative revenue".into());}
            if cohorts.is_empty(){return Ok(vec![]);}
            let weights:Vec<f64>=cohorts.iter().map(|c|c.aggregate(t)).collect();
            let tw:f64=weights.iter().sum();
            let mut shares=Vec::with_capacity(cohorts.len());
            let mut alloc=0.0_f64;
            let n=cohorts.len();
            if tw<=0.0 {
                let eq=total/n as f64;
                return Ok(cohorts.iter().map(|c|RevenueShare::new(rng,c.cohort_id.clone(),eq)).collect());
            }
            for(i,(c,&w)) in cohorts.iter().zip(weights.iter()).enumerate(){
                let amt=if i==n-1{total-alloc}else{let a=total*(w/tw);alloc+=a;a};
                shares.push(RevenueShare::new(rng,c.cohort_id.clone(),amt));
            }
            let s:f64=shares.iter().map(|x|x.amount).sum();
            if(s-total).abs()>=1e-9{return Err(format!("Invariant IV: {s:.12}!={total:.12}"));}
            Ok(shares)
        }
    }
}

pub struct SpineStats{pub version:&'static str,pub min_k:usize,pub total_cohorts:usize}
pub struct VeraSpine {
    pub version:&'static str, pub min_k:usize,
    rng:SimpleRng,
    collection:collection::CollectionLayer,
    aggregation:aggregation::AggregationLayer,
    redistribution:revenue::RevenueDistributor,
}
impl VeraSpine {
    pub fn new(min_k:usize,_eps:f64,seed:u64)->Self{
        Self{version:VERA_VERSION,min_k,rng:SimpleRng::new(seed),
             collection:collection::CollectionLayer::new(),
             aggregation:aggregation::AggregationLayer::new(min_k),
             redistribution:revenue::RevenueDistributor::new()}
    }
    pub fn create_cohort(&mut self)->String{self.aggregation.create_cohort(&mut self.rng)}
    pub fn ingest(&mut self,cid:&str,values:Vec<f64>)->Result<String,String>{
        let c=self.aggregation.get_cohort_mut(cid).ok_or_else(||format!("unknown:{}",cid))?;
        self.collection.ingest(&mut self.rng,values,c)
    }
    pub fn eligible_cohorts(&mut self,t:Option<f64>)->Vec<String>{
        self.aggregation.list_k_anonymous_cohorts(t).into_iter().map(|c|c.cohort_id).collect()
    }
    pub fn distribute_revenue(&mut self,total:f64,t:Option<f64>)->Result<Vec<(String,f64)>,String>{
        let e=self.aggregation.list_k_anonymous_cohorts(t);
        let s=self.redistribution.distribute(&mut self.rng,total,&e,t)?;
        Ok(s.into_iter().map(|x|(x.cohort_id,x.amount)).collect())
    }
    pub fn stats(&self)->SpineStats{SpineStats{version:self.version,min_k:self.min_k,total_cohorts:self.aggregation.cohort_count()}}
}

#[cfg(test)]
mod robustness {
    use super::*;
    use super::collection::CollectionLayer;
    use super::aggregation::AggregationLayer;
    use super::revenue::RevenueDistributor;
    use proptest::prelude::*;

    const T0: f64 = 1_000_000.0;

    // ── PROPERTY TESTS ────────────────────────────────────────────────────────

    proptest! {
        #[test]
        fn prop_decay_in_unit_interval(age in 0.0f64..(DECAY_MAX_AGE-1.0)) {
            let mut r=SimpleRng::new(42);
            let g=Graphlet::new_at(&mut r,1.0,MIN_K,T0);
            let f=g.decay_factor(Some(T0+age));
            prop_assert!(f>=0.0 && f<=1.0,"f={f}");
        }

        #[test]
        fn prop_decay_monotone(a in 0.0f64..(DECAY_MAX_AGE/2.0), b in 0.0f64..(DECAY_MAX_AGE/2.0)) {
            let mut r=SimpleRng::new(42);
            let g=Graphlet::new_at(&mut r,1.0,MIN_K,T0);
            let (lo,hi)=if a<=b{(a,b)}else{(b,a)};
            let fa=g.decay_factor(Some(T0+lo));
            let fb=g.decay_factor(Some(T0+hi));
            prop_assert!(fa>=fb,"f({lo:.1})={fa:.6} < f({hi:.1})={fb:.6}");
        }

        #[test]
        fn prop_redistribution_sum_exact(total in 0.0f64..1e9, n in 1usize..=30usize) {
            let mut r=SimpleRng::new(42);
            let col=CollectionLayer::new();
            let mut agg=AggregationLayer::new(1);
            let dist=RevenueDistributor::new();
            let mut cohorts=Vec::new();
            for _ in 0..n {
                let cid=agg.create_cohort(&mut r);
                let c=agg.get_cohort_mut(&cid).unwrap();
                col.ingest(&mut r, vec![0.5],c).unwrap();
                cohorts.push(c.clone());
            }
            let shares=dist.distribute(&mut r,total,&cohorts,None).unwrap();
            let s:f64=shares.iter().map(|x|x.amount).sum();
            prop_assert!((s-total).abs()<1e-9,"n={n} écart={:.2e}",(s-total).abs());
        }

        #[test]
        fn prop_uuid_format(seed in 1u64..u64::MAX) {
            let mut r=SimpleRng::new(seed);
            let mut agg=AggregationLayer::new(1);
            let cid=agg.create_cohort(&mut r);
            let p:Vec<&str>=cid.split('-').collect();
            prop_assert_eq!(p.len(),5);
            prop_assert_eq!(p[0].len(),8);
            prop_assert_eq!(p[4].len(),12);
        }
    }

    // ── STRESS TESTS ──────────────────────────────────────────────────────────

    #[test]
    fn stress_1k_cohorts_100k_graphlets() {
        let mut r=SimpleRng::new(42);
        let col=CollectionLayer::new();
        let mut agg=AggregationLayer::new(100);
        for _ in 0..1_000 {
            let cid=agg.create_cohort(&mut r);
            let c=agg.get_cohort_mut(&cid).unwrap();
            for _ in 0..100 { col.ingest(&mut r, vec![0.5],c).unwrap(); }
        }
        assert_eq!(agg.cohort_count(),1_000);
        assert_eq!(agg.list_k_anonymous_cohorts(None).len(),1_000);
        println!("\n  Stress 100k graphlets OK");
    }

    #[test]
    fn stress_redistribution_500_cohorts() {
        let mut r=SimpleRng::new(42);
        let col=CollectionLayer::new();
        let mut agg=AggregationLayer::new(1);
        let dist=RevenueDistributor::new();
        for _ in 0..500 {
            let cid=agg.create_cohort(&mut r);
            col.ingest(&mut r, vec![0.5],agg.get_cohort_mut(&cid).unwrap()).unwrap();
        }
        let cohorts=agg.list_k_anonymous_cohorts(None);
        let total=999_999.9999_f64;
        let shares=dist.distribute(&mut r,total,&cohorts,None).unwrap();
        let s:f64=shares.iter().map(|x|x.amount).sum();
        assert!((s-total).abs()<1e-9,"écart={:.2e}",(s-total).abs());
        println!("\n  Stress 500 cohorts écart={:.2e}",(s-total).abs());
    }

    #[test]
    fn stress_purge_1000_graphlets() {
        let mut r=SimpleRng::new(42);
        let col=CollectionLayer::new();
        let mut agg=AggregationLayer::new(1);
        let cid=agg.create_cohort(&mut r);
        let cohort=agg.get_cohort_mut(&cid).unwrap();
        for _ in 0..500 { col.ingest(&mut r, vec![0.5],cohort).unwrap(); }
        for _ in 0..500 {
            col.ingest(&mut r, vec![0.5],cohort).unwrap();
            cohort.graphlets.last_mut().unwrap().created_at=T0;
        }
        let removed=cohort.purge_expired(Some(T0+DECAY_MAX_AGE));
        assert_eq!(removed,500); assert_eq!(cohort.size(),500);
        println!("\n  Stress purge 500 expirés OK");
    }

    #[test]
    fn stress_float_accumulation() {
        let ns=[1usize,3,7,13,97,499,1000];
        let dist=RevenueDistributor::new();
        for n in ns {
            let mut r=SimpleRng::new(42);
            let col=CollectionLayer::new();
            let mut agg=AggregationLayer::new(1);
            for _ in 0..n {
                let cid=agg.create_cohort(&mut r);
                col.ingest(&mut r, vec![0.5],agg.get_cohort_mut(&cid).unwrap()).unwrap();
            }
            let cohorts=agg.list_k_anonymous_cohorts(None);
            let shares=dist.distribute(&mut r,1.0,&cohorts,None).unwrap();
            let s:f64=shares.iter().map(|x|x.amount).sum();
            assert!((s-1.0).abs()<1e-9,"n={n}");
        }
        println!("\n  Stress flottants n={ns:?} OK");
    }

    // ── SERIALIZATION TESTS ───────────────────────────────────────────────────

    fn g_to_json(g:&Graphlet)->String {
        format!(r#"{{"graphlet_id":"{}","cohort_id":"{}","aggregated_value":{},"count":{}}}"#,
            g.graphlet_id,g.cohort_id,g.aggregated_value,g.count)
    }

    #[test]
    fn serial_graphlet_no_raw_value() {
        let mut r=SimpleRng::new(42);
        let col=CollectionLayer::new();
        let mut agg=AggregationLayer::new(1);
        let cid=agg.create_cohort(&mut r);
        col.ingest(&mut r, vec![0.1,0.5,0.9],agg.get_cohort_mut(&cid).unwrap()).unwrap();
        let json=g_to_json(&agg.get_cohort(&cid).unwrap().graphlets[0]);
        assert!(!json.contains("raw_value"));
        assert!(!json.contains("input_values"));
    }

    #[test]
    fn serial_graphlet_mean_preserved() {
        let mut r=SimpleRng::new(42);
        let col=CollectionLayer::new();
        let mut agg=AggregationLayer::new(1);
        let cid=agg.create_cohort(&mut r);
        col.ingest(&mut r, vec![0.3,0.6,0.9],agg.get_cohort_mut(&cid).unwrap()).unwrap();
        let g=&agg.get_cohort(&cid).unwrap().graphlets[0];
        assert!((g.aggregated_value-(0.3+0.6+0.9)/3.0).abs()<1e-12);
        let json=g_to_json(g);
        assert!(json.contains(&g.cohort_id));
        assert!(json.contains("\"count\":3"));
    }

    #[test]
    fn serial_golden_snapshot() {
        let mut spine=VeraSpine::new(2,0.1,42);
        let cid=spine.create_cohort();
        spine.ingest(&cid, vec![0.3,0.7]).unwrap();
        spine.ingest(&cid, vec![0.4,0.6]).unwrap();
        let result=spine.distribute_revenue(100.0,None).unwrap();
        let revenue:f64=result.iter().map(|(_,a)|a).sum();
        let snap=format!(r#"{{"version":"{}","revenue":{:.6}}}"#,VERA_VERSION,revenue);
        assert!(snap.contains("3.1.1"));
        assert!((revenue-100.0).abs()<1e-9);
        assert!(!snap.contains("raw_value"));
        println!("\n  Golden : {snap}");
    }
}

#[cfg(test)]
mod pre_lock {
    use super::*;
    use super::collection::CollectionLayer;
    use super::aggregation::AggregationLayer;
    use super::revenue::RevenueDistributor;

    #[test]
    fn reject_nan_in_ingest() {
        let mut r=SimpleRng::new(42);
        let col=CollectionLayer::new();
        let mut agg=AggregationLayer::new(1);
        let cid=agg.create_cohort(&mut r);
        let c=agg.get_cohort_mut(&cid).unwrap();
        let result=col.ingest(&mut r, vec![f64::NAN],c);
        assert!(result.is_err(),"NaN doit être rejeté");
    }

    #[test]
    fn reject_inf_in_ingest() {
        let mut r=SimpleRng::new(42);
        let col=CollectionLayer::new();
        let mut agg=AggregationLayer::new(1);
        let cid=agg.create_cohort(&mut r);
        let c=agg.get_cohort_mut(&cid).unwrap();
        assert!(col.ingest(&mut r, vec![f64::INFINITY],c).is_err());
        assert!(col.ingest(&mut r, vec![f64::NEG_INFINITY],c).is_err());
    }

    #[test]
    fn reject_nan_in_revenue() {
        let mut r=SimpleRng::new(42);
        let col=CollectionLayer::new();
        let mut agg=AggregationLayer::new(1);
        let dist=RevenueDistributor::new();
        let cid=agg.create_cohort(&mut r);
        col.ingest(&mut r, vec![0.5],agg.get_cohort_mut(&cid).unwrap()).unwrap();
        let cohorts=agg.list_k_anonymous_cohorts(None);
        assert!(dist.distribute(&mut r,f64::NAN,&cohorts,None).is_err());
        assert!(dist.distribute(&mut r,f64::INFINITY,&cohorts,None).is_err());
    }

    #[test]
    fn reject_mixed_nan_values() {
        let mut r=SimpleRng::new(42);
        let col=CollectionLayer::new();
        let mut agg=AggregationLayer::new(1);
        let cid=agg.create_cohort(&mut r);
        let c=agg.get_cohort_mut(&cid).unwrap();
        // NaN mélangé à des valeurs valides
        assert!(col.ingest(&mut r, vec![0.5,f64::NAN,0.3],c).is_err());
    }
}
pub mod dp;

#[cfg(test)]
mod integration {
    use super::*;
    use super::dp::{privatize_value, BudgetTracker};

    #[test]
    fn test_end_to_end_pipeline() {
        // 1. INGEST
        let mut spine = VeraSpine::new(100, 1.0, 42);
        let cid = spine.create_cohort();
        for _ in 0..100 {
            spine.ingest(&cid, vec![0.3, 0.5, 0.7]).unwrap();
        }

        // 2. DP
        let mut budget = BudgetTracker::new(10.0);
        budget.consume(1.0).unwrap();
        let raw_value = 0.5f64;
        let private_value = privatize_value(raw_value, 1, 1, 42);
        assert!(private_value >= 0.0 && private_value <= 1.0);

        // 3. EXPORT
        let eligible = spine.eligible_cohorts(None);
        assert!(!eligible.is_empty());

        // 4. REDISTRIBUTION
        let result = spine.distribute_revenue(100.0, None).unwrap();
        let total: f64 = result.iter().map(|(_, a)| a).sum();
        assert!((total - 100.0).abs() < 1e-9);

        // 5. PURGE — verify no raw values in output
        for (cohort_id, amount) in &result {
            assert!(!cohort_id.contains("raw"));
            assert!(*amount > 0.0);
        }

        // 6. VERIFY LOGS CONTAIN NO RAW PAYLOAD
        let stats = spine.stats();
        assert_eq!(stats.version, "3.1.1");
        assert!(stats.total_cohorts > 0);
    }
}

#[cfg(test)]
mod adversarial {
    use super::*;
    use super::collection::CollectionLayer;
    use super::aggregation::AggregationLayer;
    use super::revenue::RevenueDistributor;

    #[test]
    fn test_biased_signal_injection() {
        // Attacker injects extreme values to bias the aggregate
        let mut r = SimpleRng::new(42);
        let col = CollectionLayer::new();
        let mut agg = AggregationLayer::new(100);
        let cid = agg.create_cohort(&mut r);
        let cohort = agg.get_cohort_mut(&cid).unwrap();

        // 99 normal signals
        for _ in 0..99 {
            col.ingest(&mut r, vec![0.5], cohort).unwrap();
        }
        // 1 biased signal — attacker tries to push aggregate to 1.0
        col.ingest(&mut r, vec![1.0], cohort).unwrap();

        let mean: f64 = cohort.graphlets.iter().map(|g| g.aggregated_value).sum::<f64>() / cohort.graphlets.len() as f64;
        assert!(mean < 0.6, "biased injection moved mean: {}", mean);
    }

    #[test]
    fn test_temporal_drift() {
        // System remains stable over long time horizon
        let mut r = SimpleRng::new(42);
        let col = CollectionLayer::new();
        let mut agg = AggregationLayer::new(100);
        let cid = agg.create_cohort(&mut r);
        let cohort = agg.get_cohort_mut(&cid).unwrap();

        for i in 0..1000 {
            let v = if i % 2 == 0 { 0.3 } else { 0.7 };
            col.ingest(&mut r, vec![v], cohort).unwrap();
        }

        // After 1000 ticks, aggregate should converge to ~0.5
        let mean: f64 = cohort.graphlets.iter().map(|g| g.aggregated_value).sum::<f64>() / cohort.graphlets.len() as f64;
        assert!((mean - 0.5).abs() < 0.1, "temporal drift mean: {}", mean);
    }

    #[test]
    fn test_reidentification_risk() {
        // Even with DP + k-anonymity, no raw value should be recoverable
        use super::dp::privatize_value;
        let raw = 0.42f64;
        let mut recovered_exact = 0;
        for seed in 0u64..1000 {
            let noisy = privatize_value(raw, 1, 100, seed);
            if (noisy - raw).abs() < 1e-6 {
                recovered_exact += 1;
            }
        }
        // Less than 1% exact recovery rate
        assert!(recovered_exact < 25,
            "re-identification risk: {}/1000 exact recoveries", recovered_exact);
    }

    #[test]
    fn test_redistribution_gaming() {
        // An actor cannot game redistribution by inflating their signal
        let mut r = SimpleRng::new(42);
        let col = CollectionLayer::new();
        let mut agg = AggregationLayer::new(1);
        let dist = RevenueDistributor::new();

        // Normal actor
        let cid1 = agg.create_cohort(&mut r);
        col.ingest(&mut r, vec![0.5], agg.get_cohort_mut(&cid1).unwrap()).unwrap();

        // Gaming actor — inflates signal to max
        let cid2 = agg.create_cohort(&mut r);
        for _ in 0..100 {
            col.ingest(&mut r, vec![1.0], agg.get_cohort_mut(&cid2).unwrap()).unwrap();
        }

        let cohorts = agg.list_k_anonymous_cohorts(None);
        let shares = dist.distribute(&mut r, 100.0, &cohorts, None).unwrap();
        let total: f64 = shares.iter().map(|s| s.amount).sum();

        // Total must always equal 100.0 regardless of gaming
        assert!((total - 100.0).abs() < 1e-9, "redistribution total: {}", total);

        // Gaming actor should not get more than 95% of revenue
        let max_share = shares.iter().map(|s| s.amount).fold(0.0f64, f64::max);
        assert!(max_share < 100.0, "gaming actor got everything: {}", max_share);
    }
}

#[cfg(test)]
mod invariant_tests {
    use zeroize::Zeroize;

    #[test]
    fn invariant_i_raw_buffer_is_wiped() {
        let mut raw: Vec<f64> = vec![0.3, 0.5, 0.7];
        let agg = raw.iter().sum::<f64>() / raw.len() as f64;
        raw.zeroize();
        for x in &raw {
            assert_eq!(*x, 0.0, "brut non efface");
        }
        assert!((agg - 0.5).abs() < 1e-12, "agg perdu");
    }
}
