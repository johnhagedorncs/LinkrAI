# Practice 1959222 - Quick Reference

> **Practice ID:** 1959222
> **For scheduling Internal Medicine referrals**

---

## Appointment Type

| ID | Name | Duration |
|----|------|----------|
| 62 | Consult | 30 min |

---

## Provider-Department Pairs

| Provider ID | Provider Name | Dept ID | Department | Location |
|-------------|---------------|---------|------------|----------|
| 67 | Chip Ach | 155 | kate DEPT | Norwood, MA |
| 86 | Laura Dodge | 155 | kate DEPT | Norwood, MA |
| 21 | Pierce Hawkeye | 168 | Springfield Medical | Dedham, MA |
| 77 | Joshua Parker | 168 | Springfield Medical | Dedham, MA |
| 68 | Luvenia Smith | 149 | Ortho OP | Boston, MA |

---

## Schedule Availability

| Provider | Days | Hours |
|----------|------|-------|
| Chip Ach (67) | M/T/Th, Fri AM | 6:30am-2:30pm |
| Laura Dodge (86) | T/W/Th/F | 9:00am-5:00pm |
| Pierce Hawkeye (21) | M/T/W/F | 8:00am-4:00pm |
| Joshua Parker (77) | T/Th | 1:00pm-5:00pm |
| Luvenia Smith (68) | M/T/Th/F | 11:00am-7:00pm |

---

## API Quick Reference

**Find open slots:**
```
GET /v1/{practiceid}/appointments/open
  providerid: [67|86|21|77|68]
  departmentid: [155|168|149]
  appointmenttypeid: 62
```

**Book appointment:**
```
POST /v1/{practiceid}/appointments/{appointmentid}
  appointmenttypeid: 62
  patientid: [patient_id]
```

**Create slot:**
```
POST /v1/{practiceid}/appointments/open
  providerid: [provider_id]
  departmentid: [dept_id]
  appointmenttypeid: 62
  appointmentdate: MM/DD/YYYY
  appointmenttime: HH:MM
```
