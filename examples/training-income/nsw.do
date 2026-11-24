version 16.0
* Run from the training-income example directory.
preserve
set more off
set linesize 150
log using "nsw_results.log", text replace name(trainingpilot)
capture confirm file "data/nsw_dw.dta"
if _rc {
    capture mkdir data
    copy "https://users.nber.org/~rdehejia/data/nsw_dw.dta" "data/nsw_dw.dta"
}
use "data/nsw_dw.dta", clear
describe
tabulate data_id, missing
tabulate treat, missing
local baseline age education black hispanic married nodegree re74 re75
misstable summarize treat re78 `baseline', all
tabstat re74 re75 re78, by(treat) statistics(n mean min max) columns(statistics)
generate byte common = !missing(treat,re78,age,education,black,hispanic,married,nodegree,re74,re75)
tabulate treat common, missing
quietly summarize re78 if common & treat==0
local controlmean = r(mean)
local controls = r(N)
quietly summarize re78 if common & treat==1
local treatedmean = r(mean)
local treated = r(N)
tempname out
tempfile modelrows
postfile `out' str12 specification int n0 n1 double mean0 mean1 difference robustse lo95 hi95 p using `modelrows'
foreach model in unadjusted adjusted {
    local covariates
    if "`model'" == "adjusted" local covariates `baseline'
    regress re78 treat `covariates' if common, vce(robust)
    lincom treat, level(95)
    post `out' ("`model'") (`controls') (`treated') (`controlmean') (`treatedmean') (r(estimate)) (r(se)) (r(lb)) (r(ub)) (r(p))
}
postclose `out'
use `modelrows', clear
list, noobs abbreviate(16)
export delimited using "nsw_results.csv", replace
log close trainingpilot
restore
