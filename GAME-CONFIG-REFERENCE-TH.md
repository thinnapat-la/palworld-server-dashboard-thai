# คู่มือ Config เกม Palworld ฉบับเต็ม (ภาษาไทย)

> สำหรับ **Palworld Server & Dashboard Thai Edition 1.1.0**  
> อ้างอิงชุดค่า `DefaultPalWorldSettings.ini` ของ Palworld 1.0 จำนวน **119 ค่า**  
> ปรับปรุงข้อมูล: 19 กรกฎาคม 2026

ไฟล์นี้อธิบายว่าแต่ละค่าคืออะไร ค่า Default เท่าไร เพิ่มหรือลดแล้วเกิดอะไรขึ้น พร้อมตัวอย่างที่นำไปใช้จริงได้ โดยคงชื่อ Key ตามเกมทุกตัว รวมถึงชื่อที่สะกดผิดจากต้นฉบับ เช่น `Decreace` และ `Regene` ซึ่ง **ห้ามแก้การสะกดเอง**

---

## วิธีแก้ที่ง่ายที่สุดในโปรเจกต์นี้

1. เปิด Dashboard
2. เข้าเมนู **Config**
3. ค้นหาชื่อค่า เช่น `ItemWeightRate`
4. ใส่ค่าใหม่แล้วกด **เก็บค่า**
5. กด **อัปเดตไฟล์** และตรวจว่าระบบแจ้งว่าบันทึกสำเร็จ
6. กด **Restart Server** แยกต่างหาก
7. รอ Server และ REST API กลับมา Online

Dashboard จะเขียนไฟล์จริงตามระบบ:

```text
Windows: <PALWORLD_HOST_DIR>/Pal/Saved/Config/WindowsServer/PalWorldSettings.ini
Linux:  /palworld/Pal/Saved/Config/LinuxServer/PalWorldSettings.ini
macOS:  ใช้ LinuxServer ภายใน Docker เช่นเดียวกับ Linux
```

> หน้าแก้ค่าแบบรายการจะแสดง Key ที่ Server ส่งจาก `GET /settings` หากต้องการเพิ่ม Key ที่ยังไม่มีในไฟล์ ให้ใช้ **Advanced editor: PalWorldSettings.ini** และใส่ Key ภายใน `OptionSettings=(...)`

---

## หลักการอ่านค่าอย่างรวดเร็ว

| รูปแบบ | ความหมายทั่วไป |
|---|---|
| `True` / `False` | เปิด / ปิดฟีเจอร์ |
| ตัวคูณ `1` | ค่าเดิม 100% |
| ตัวคูณ `0.5` | ครึ่งหนึ่ง แต่ต้องดูว่าค่านั้นคูณ “ความเร็ว” หรือ “ระยะเวลา/ความเสียหายที่ได้รับ” |
| ตัวคูณ `2` | สองเท่า |
| `0` | หลายค่าหมายถึงปิดผลนั้น เช่น น้ำหนัก 0 หรือ Durability loss 0 แต่บางค่าอาจทำงานผิดปกติ จึงต้องดูคำอธิบายรายตัว |
| `-1` | ใช้เฉพาะบางค่า เช่น `PhysicsActiveDropItemMaxNum=-1` หมายถึงไม่จำกัด |

### ตัวอย่าง `ItemWeightRate`

| ค่า | ผล |
|---:|---|
| `0` | ไอเทมไม่มีน้ำหนัก |
| `0.5` | ไอเทมหนักครึ่งหนึ่ง แบกได้มากขึ้นประมาณ 2 เท่า |
| `1` | Default |
| `2` | ไอเทมหนัก 2 เท่า แบกได้น้อยลง |
| `5` | ไอเทมหนักมาก เหมาะกับ Challenge server |

---

## คำเตือนก่อนเปลี่ยนค่า

- กด **Export** หรือสร้าง Backup ก่อนแก้หลายค่า
- ค่า Config มีผลหลัง Restart Server
- `AdminPassword`, REST API และ RCON ต้องตรงกับ `.env` หรือ `.env.host` ของโปรเจกต์
- ห้ามเปิด REST API หรือ RCON ออก Internet โดยตรง
- ค่าที่เพิ่มจำนวน Pal, ฐาน, Worker, อาคาร และไอเทมตกพื้นสามารถเพิ่ม CPU/RAM/Network load มาก
- World ที่ย้ายมาจาก Single-player/Co-op อาจมี `WorldOption.sav` ซึ่งเขียนทับค่า Gameplay หลายตัวจาก `PalWorldSettings.ini`; ดูหัวข้อแก้ปัญหาท้ายไฟล์

---

## รายการค่าทั้งหมด 119 ค่า

### 1. ระดับความยากและ Randomizer

| Key | Default | ความหมาย | ค่าและทิศทาง | ตัวอย่างใช้งาน | หมายเหตุ |
|---|---:|---|---|---|---|
| `Difficulty` | `None` | Preset ความยากหลักของโลก | `None`, `Casual`, `Normal`, `Hard`<br>`None` ให้ใช้ค่ารายตัวด้านล่าง; preset อื่นอาจปรับหลายค่าเป็นชุด | ต้องการกำหนด EXP/ดาเมจเองให้ใช้ `None` | อย่าคาดว่าปรับ ExpRate แล้วจะได้ผลตามต้องการหาก preset ของเกมเขียนทับ |
| `RandomizerType` | `None` | รูปแบบสุ่มชนิด Pal ที่เกิดในโลก | `None`, `Region`, `All`<br>`None` ปิด; `Region` สุ่มภายในแต่ละภูมิภาค; `All` สุ่มทั้งโลก | `Region` เหมาะกับโลกสุ่มที่ยังคงโครงพื้นที่โดยรวม | เปลี่ยนในโลกที่เล่นไปแล้วอาจให้ผลต่างจากโลกใหม่ |
| `RandomizerSeed` | `""` | Seed สำหรับระบบสุ่ม Pal | ข้อความ เช่น `"my-seed"`; ว่าง = ให้เกมเลือก<br>Seed เดิมช่วยให้ผลสุ่มทำซ้ำได้เมื่อเงื่อนไขอื่นเหมือนกัน | `RandomizerSeed="thai-server-01"` | มีผลเมื่อ RandomizerType ไม่ใช่ `None` |
| `bIsRandomizerPalLevelRandom` | `False` | กำหนดวิธีสุ่มเลเวล Pal เมื่อเปิด Randomizer | `True` / `False`<br>`False` ยังอิงช่วงเลเวลเหมาะสมของพื้นที่; `True` สุ่มเลเวลเต็มรูปแบบ | ใช้ `False` ถ้าต้องการ progression ที่ไม่เหวี่ยงเกินไป | มีผลเมื่อเปิด Randomizer |

### 2. เวลา การเติบโต และอัตราคูณหลัก

| Key | Default | ความหมาย | ค่าและทิศทาง | ตัวอย่างใช้งาน | หมายเหตุ |
|---|---:|---|---|---|---|
| `DayTimeSpeedRate` | `1.000000` | ความเร็วที่เวลากลางวันเดิน | ตัวเลขตั้งแต่ `0` ขึ้นไป; ปกติ `1`<br>มากกว่า 1 = กลางวันผ่านเร็ว/สั้นลง; ต่ำกว่า 1 = กลางวันยาวขึ้น | `0.5` กลางวันประมาณ 2 เท่านาน, `2` สั้นประมาณครึ่งหนึ่ง | ไม่แนะนำ `0` เพราะอาจทำให้เวลาค้างหรือระบบตามเวลาไม่เดิน |
| `NightTimeSpeedRate` | `1.000000` | ความเร็วที่เวลากลางคืนเดิน | ตัวเลขตั้งแต่ `0` ขึ้นไป; ปกติ `1`<br>มากกว่า 1 = กลางคืนผ่านเร็ว/สั้นลง; ต่ำกว่า 1 = กลางคืนยาวขึ้น | `2` ทำให้กลางคืนสั้นประมาณครึ่งหนึ่ง | ไม่แนะนำ `0` |
| `ExpRate` | `1.000000` | ตัวคูณ EXP ของผู้เล่นและ Pal | ตัวเลข `0` ขึ้นไป; ปกติ `1`<br>เพิ่ม = ได้ EXP มากขึ้น; ลด = โตช้าลง | `0.5` ครึ่งหนึ่ง, `2` สองเท่า, `5` ห้าเท่า | ค่าสูงมากทำให้ progression จบเร็ว |
| `PalCaptureRate` | `1.000000` | ตัวคูณโอกาสจับ Pal | ตัวเลข `0` ขึ้นไป; ปกติ `1`<br>เพิ่ม = จับง่ายขึ้น; ลด = จับยากขึ้น | `0.5` ยากขึ้น, `1.5` ง่ายขึ้น, `2` ง่ายมากขึ้น | ไม่ใช่เปอร์เซ็นต์สำเร็จตรง ๆ และไม่รับประกัน 100% |
| `PalSpawnNumRate` | `1.000000` | ตัวคูณจำนวน Pal ป่าที่เกิด | ตัวเลข `0` ขึ้นไป; ปกติ `1`<br>เพิ่ม = Pal เกิดมากขึ้น; ลด = น้อยลง | `0.5` ลดจำนวน, `2` ประมาณสองเท่า | กระทบ CPU/RAM อย่างชัดเจน ควรเพิ่มทีละน้อย |
| `PalEggDefaultHatchingTime` | `1.000000` | เวลาฟักไข่ขนาดใหญ่ หน่วยชั่วโมง | ตัวเลข `0` ขึ้นไป<br>ลด = ฟักเร็ว; `0` = ฟักทันที; ไข่ขนาดอื่นปรับตามสัดส่วน | `0.5` ราว 30 นาทีสำหรับไข่ใหญ่, `2` ราว 2 ชั่วโมง | เป็นเวลาอ้างอิงของไข่ใหญ่ |
| `WorkSpeedRate` | `1.000000` | ตัวคูณความเร็วทำงาน/ผลิต/ก่อสร้าง | ตัวเลข `0` ขึ้นไป; ปกติ `1`<br>เพิ่ม = งานเสร็จเร็ว; ลด = ช้าลง; `0` อาจทำให้งานไม่เดิน | `1.5` เร็วขึ้น 50%, `2` สองเท่า | ค่าแรงงานจำนวนมากร่วมกับค่านี้อาจเพิ่มโหลด |
| `SupplyDropSpan` | `180` | ช่วงระหว่าง Supply Drop/อุกกาบาต หน่วยนาที | จำนวนเต็มบวก<br>ลด = Event เกิดถี่ขึ้น; เพิ่ม = ห่างขึ้น | `60` ทุก 1 ชั่วโมง, `180` ทุก 3 ชั่วโมง | ไม่แนะนำ `0` เพราะอาจเกิดถี่ผิดปกติหรือถูกเกมบังคับค่า |
| `MonsterFarmActionSpeedRate` | `1.000000` | ตัวคูณความเร็วผลิตไอเทมที่ Ranch/Monster Farm | ตัวเลข `0` ขึ้นไป; ปกติ `1`<br>เพิ่ม = ผลิตเร็วขึ้น; ลด = ช้าลง; `0` หยุด/แทบไม่ผลิต | `2` ผลิตราวสองเท่า | ขึ้นกับรอบ AI และชนิด Pal ด้วย |

### 3. ดาเมจ ความหิว Stamina และการฟื้นฟู

| Key | Default | ความหมาย | ค่าและทิศทาง | ตัวอย่างใช้งาน | หมายเหตุ |
|---|---:|---|---|---|---|
| `PalDamageRateAttack` | `1.000000` | ดาเมจที่ Pal เป็นฝ่ายโจมตี | ตัวคูณ; ปกติ `1`<br>เพิ่ม = Pal ตีแรงขึ้น; ลด = เบาลง; `0` แทบไม่ทำดาเมจ | `0.5` ครึ่งหนึ่ง, `2` สองเท่า | - |
| `PalDamageRateDefense` | `1.000000` | ดาเมจที่ Pal ได้รับ | ตัวคูณ; ปกติ `1`<br>เพิ่ม = Pal โดนแรงขึ้น/ตายง่าย; ลด = ถึกขึ้น; `0` อาจแทบไม่รับดาเมจ | `0.5` รับครึ่งหนึ่ง, `2` รับสองเท่า | ชื่อ Defense ทำให้สับสน แต่ค่านี้คูณดาเมจที่ Pal ได้รับ |
| `PlayerDamageRateAttack` | `1.000000` | ดาเมจที่ผู้เล่นเป็นฝ่ายโจมตี | ตัวคูณ; ปกติ `1`<br>เพิ่ม = ผู้เล่นตีแรงขึ้น; ลด = เบาลง | `2` ทำดาเมจสองเท่า | - |
| `PlayerDamageRateDefense` | `1.000000` | ดาเมจที่ผู้เล่นได้รับ | ตัวคูณ; ปกติ `1`<br>เพิ่ม = ผู้เล่นโดนแรงขึ้น; ลด = ถึกขึ้น; `0` อาจแทบไม่รับดาเมจ | `0.5` รับครึ่งหนึ่ง, `2` รับสองเท่า | ชื่อ Defense ทำให้สับสน แต่ค่านี้คูณดาเมจที่ได้รับ |
| `PlayerStomachDecreaceRate` | `1.000000` | อัตราลดความอิ่มของผู้เล่น | ตัวคูณ; ปกติ `1`<br>เพิ่ม = หิวเร็ว; ลด = หิวช้า; `0` = ความหิวไม่ลดหรือแทบไม่ลด | `0.5` หิวช้าประมาณครึ่งหนึ่ง, `2` หิวเร็วสองเท่า | สะกด `Decreace` ตามชื่อจริงของเกม |
| `PlayerStaminaDecreaceRate` | `1.000000` | อัตราใช้ Stamina ของผู้เล่น | ตัวคูณ; ปกติ `1`<br>เพิ่ม = Stamina หมดเร็ว; ลด = ใช้น้อย; `0` = แทบไม่ลด | `0.5` วิ่ง/ปีนได้นานขึ้นประมาณสองเท่า | - |
| `PlayerAutoHPRegeneRate` | `1.000000` | อัตราฟื้น HP อัตโนมัติของผู้เล่น | ตัวคูณ; ปกติ `1`<br>เพิ่ม = ฟื้นเร็ว; ลด = ฟื้นช้า; `0` = ไม่ฟื้นอัตโนมัติ | `2` ฟื้นสองเท่า | - |
| `PlayerAutoHpRegeneRateInSleep` | `1.000000` | อัตราฟื้น HP ผู้เล่นขณะนอน | ตัวคูณ; ปกติ `1`<br>เพิ่ม = ฟื้นขณะนอนเร็วขึ้น; `0` = ไม่ฟื้นจากกลไกนี้ | `5` เหมาะกับเซิร์ฟเล่นสบาย | - |
| `PalStomachDecreaceRate` | `1.000000` | อัตราลดความอิ่มของ Pal | ตัวคูณ; ปกติ `1`<br>เพิ่ม = Pal หิวเร็ว; ลด = หิวช้า; `0` = แทบไม่หิว | `0.5` ลดการกินอาหารประมาณครึ่งหนึ่ง | - |
| `PalStaminaDecreaceRate` | `1.000000` | อัตราใช้ Stamina ของ Pal | ตัวคูณ; ปกติ `1`<br>เพิ่ม = หมดเร็ว; ลด = ใช้น้อย; `0` = แทบไม่ลด | `0.5` Pal ทำกิจกรรมได้นานขึ้น | - |
| `PalAutoHPRegeneRate` | `1.000000` | อัตราฟื้น HP อัตโนมัติของ Pal | ตัวคูณ; ปกติ `1`<br>เพิ่ม = ฟื้นเร็ว; ลด = ฟื้นช้า; `0` = ไม่ฟื้นอัตโนมัติ | `2` ฟื้นสองเท่า | - |
| `PalAutoHpRegeneRateInSleep` | `1.000000` | อัตราฟื้น HP ของ Pal ขณะพัก/อยู่ Palbox | ตัวคูณ; ปกติ `1`<br>เพิ่ม = ฟื้นเร็วใน Palbox; `0` = ไม่ฟื้นจากกลไกนี้ | `5` ฟื้นเร็วมากใน Palbox | - |

### 4. ไอเทม ทรัพยากร สิ่งปลูกสร้าง และความทนทาน

| Key | Default | ความหมาย | ค่าและทิศทาง | ตัวอย่างใช้งาน | หมายเหตุ |
|---|---:|---|---|---|---|
| `BuildObjectHpRate` | `1.000000` | ตัวคูณ HP ของสิ่งปลูกสร้าง | ตัวเลข `0` ขึ้นไป; ปกติ `1`<br>เพิ่ม = อาคารมี HP มากขึ้น; ลด = พังง่ายขึ้น | `0.5` HP ครึ่งหนึ่ง, `2` HP สองเท่า | ไม่แนะนำ `0` |
| `BuildObjectDamageRate` | `1.000000` | ตัวคูณดาเมจที่กระทำต่อสิ่งปลูกสร้าง | ตัวเลข `0` ขึ้นไป; ปกติ `1`<br>เพิ่ม = อาคารถูกทำลายเร็ว; ลด = อาคารทนขึ้น; `0` อาจไม่รับดาเมจ | `0.5` อาคารรับดาเมจครึ่งหนึ่ง, `2` สองเท่า | - |
| `BuildObjectDeteriorationDamageRate` | `1.000000` | ตัวคูณความเสียหายจากการเสื่อมสภาพของอาคาร | ตัวเลข `0` ขึ้นไป; ปกติ `1`<br>เพิ่ม = เสื่อมเร็ว; ลด = เสื่อมช้า; `0` = ปิด/แทบไม่มี decay | `0` นิยมใช้เพื่อไม่ให้อาคารนอกฐานผุ | - |
| `CollectionDropRate` | `1.000000` | ตัวคูณจำนวนทรัพยากรที่ได้จากต้นไม้ แร่ และจุดเก็บ | ตัวเลข `0` ขึ้นไป; ปกติ `1`<br>เพิ่ม = ได้ของมากขึ้น; ลด = ได้น้อยลง; `0` = อาจไม่ดรอป | `2` ได้ทรัพยากรราวสองเท่า | - |
| `CollectionObjectHpRate` | `1.000000` | ตัวคูณ HP ของจุดทรัพยากร | ตัวเลข `0` ขึ้นไป; ปกติ `1`<br>เพิ่ม = ต้องตีหลายครั้งขึ้น; ลด = แตกเร็วขึ้น | `0.5` แตกเร็ว, `2` ใช้เวลาตีนานขึ้น | ไม่ใช่ตัวคูณจำนวนไอเทมโดยตรง |
| `CollectionObjectRespawnSpeedRate` | `1.000000` | ตัวคูณช่วงเวลารอเกิดใหม่ของจุดทรัพยากร | ตัวเลขมากกว่า `0`; ปกติ `1`<br>ค่าน้อย = เกิดใหม่เร็ว; ค่ามาก = เกิดใหม่ช้า | `0.5` รอประมาณครึ่งเวลา, `2` รอประมาณสองเท่า | ชื่อมีคำว่า Speed แต่เอกสารอธิบายเป็น Respawn interval |
| `EnemyDropItemRate` | `1.000000` | ตัวคูณจำนวนไอเทมจากศัตรู | ตัวเลข `0` ขึ้นไป; ปกติ `1`<br>เพิ่ม = ดรอปมาก; ลด = ดรอปน้อย; `0` = ไม่ดรอปหรือแทบไม่ดรอป | `2` ของราวสองเท่า | - |
| `DropItemMaxNum` | `3000` | จำนวนไอเทมตกพื้นสูงสุดทั้งโลก | จำนวนเต็มไม่ติดลบ<br>เพิ่ม = เก็บของตกพื้นได้มากแต่ใช้ RAM/CPU; ลด = ของเก่าถูกล้างเร็วขึ้น | `1500` ลดโหลด, `3000` Default, `6000` เก็บมากขึ้น | ไม่แนะนำ `0` เว้นแต่ทดสอบ เพราะอาจทำให้ของตกพื้นหายทันที |
| `PhysicsActiveDropItemMaxNum` | `-1` | จำนวนไอเทมตกพื้นสูงสุดที่จำลอง Physics พร้อมกัน | จำนวนเต็ม; `-1` = ไม่จำกัด<br>ลดค่าช่วยลด Physics load; `0` อาจปิด Physics ของไอเทมตกพื้น | `500` จำกัด Physics, `-1` ไม่จำกัด | ควรใช้เมื่อมีของตกพื้นจำนวนมาก |
| `DropItemMaxNum_UNKO` | `100` | จำนวนไอเทม UNKO/มูล Pal ที่ตกพื้นสูงสุด | จำนวนเต็มไม่ติดลบ<br>เพิ่ม = เก็บไว้มากแต่เพิ่มวัตถุในโลก; ลด = ล้างเร็ว | `0` ใช้คู่กับปิด bActiveUNKO, `100` Default | เป็นค่าขั้นสูง/เชิงทดลอง |
| `DropItemAliveMaxHours` | `1.000000` | อายุไอเทมตกพื้นก่อนถูกลบ หน่วยชั่วโมง | ตัวเลข `0` ขึ้นไป<br>เพิ่ม = ของอยู่นานขึ้นแต่สะสมมาก; ลด = ล้างเร็ว | `0.5` 30 นาที, `1` 1 ชั่วโมง, `24` 1 วัน | ค่าสูงร่วมกับ DropItemMaxNum สูงเพิ่มโหลด |
| `ItemWeightRate` | `1.000000` | ตัวคูณน้ำหนักไอเทมทั้งหมด | ตัวเลข `0` ขึ้นไป; ปกติ `1`<br>เพิ่ม = ไอเทมหนักขึ้น; ลด = เบาลง; `0` = ไอเทมไม่มีน้ำหนัก | `0` ไม่มีน้ำหนัก, `0.5` เบาครึ่งหนึ่ง, `2` หนักสองเท่า | ตรงกับตัวอย่างที่ถาม: ค่ายิ่งมากยิ่งแบกได้น้อย |
| `MaxBuildingLimitNum` | `0` | จำนวนสิ่งปลูกสร้างสูงสุดต่อผู้เล่น | จำนวนเต็ม; `0` = ไม่จำกัด<br>เพิ่มเพดานให้สร้างมากขึ้น; ลดช่วยควบคุมโหลด | `0` ไม่จำกัด, `5000` จำกัด 5,000 ชิ้น | ข้อจำกัดรายผู้เล่น ไม่ใช่จำนวนฐาน |
| `EquipmentDurabilityDamageRate` | `1.000000` | ตัวคูณการสูญเสียความทนทานของอุปกรณ์ | ตัวเลข `0` ขึ้นไป; ปกติ `1`<br>เพิ่ม = พังเร็ว; ลด = พังช้า; `0` = ไม่เสีย Durability | `0.5` อุปกรณ์อยู่ได้นานประมาณสองเท่า, `2` พังเร็วสองเท่า | - |
| `ItemCorruptionMultiplier` | `1.000000` | ตัวคูณความเร็วเน่าเสีย/เสื่อมของไอเทมที่มีอายุ | ตัวเลข `0` ขึ้นไป; ปกติ `1`<br>เพิ่ม = เน่าเร็ว; ลด = อยู่ได้นาน; `0` = ไม่เน่า | `0.5` อายุอาหารประมาณสองเท่า, `2` อายุประมาณครึ่งหนึ่ง | - |

### 6. PvP การตาย Hardcore และ Respawn

| Key | Default | ความหมาย | ค่าและทิศทาง | ตัวอย่างใช้งาน | หมายเหตุ |
|---|---:|---|---|---|---|
| `DeathPenalty` | `Item` | ของที่เสียเมื่อตาย | `None`, `Item`, `ItemAndEquipment`, `All`<br>ระดับสูงขึ้นทำให้เสียของมากขึ้น | `None` ไม่ตก, `Item` ตกของแต่ไม่รวมอุปกรณ์, `ItemAndEquipment` ตกของและอุปกรณ์, `All` รวม Pal ในทีม | Default รุ่น 1.0 คือ `Item` |
| `bEnablePlayerToPlayerDamage` | `False` | อนุญาตให้ผู้เล่นทำดาเมจใส่กัน | `True` / `False`<br>`True` ยิง/ตีผู้เล่นอื่นได้ | ปกติใช้ `True` คู่กับ bIsPvP=True | - |
| `bEnableFriendlyFire` | `False` | อนุญาต Friendly Fire ต่อพวกเดียวกัน | `True` / `False`<br>`True` ทำดาเมจคนฝ่าย/กิลด์เดียวกันได้ | เซิร์ฟ Co-op ใช้ `False` | - |
| `bIsPvP` | `False` | เปิดโหมด PvP ของโลก | `True` / `False`<br>`True` เปิดกติกา PvP; `False` PvE | เปิด PvP ควรตรวจค่าดาเมจ การดรอป และฐานร่วมกัน | - |
| `bHardcore` | `False` | เปิด Hardcore ที่การตายมีผลถาวร | `True` / `False`<br>`True` ผู้เล่นไม่สามารถ Respawn แบบปกติ | ควร Export backup ก่อนเปิด | ใช้ร่วมกับ bCharacterRecreateInHardcore และ bPalLost |
| `bPalLost` | `False` | ทำให้ Pal สูญหายถาวรเมื่อตายตามโหมด | `True` / `False`<br>`True` Pal ที่เกี่ยวข้องกับการตายอาจสูญหายถาวร | เหมาะกับ Hardcore เท่านั้น | ทดสอบก่อนใช้กับ World หลัก |
| `bCharacterRecreateInHardcore` | `False` | อนุญาตสร้างตัวละครใหม่หลังตายใน Hardcore | `True` / `False`<br>`True` เริ่มตัวละครใหม่ได้; `False` อาจปิดโอกาสกลับเข้าเล่นด้วยตัวละครเดิม | ใช้ตามนโยบาย Hardcore ของเซิร์ฟ | - |
| `bCanPickupOtherGuildDeathPenaltyDrop` | `False` | อนุญาตเก็บถุงของตายของกิลด์อื่น | `True` / `False`<br>`True` ผู้อื่น Loot ของที่ตกจากการตายได้ | PvP แบบ Loot ใช้ `True`; Co-op ใช้ `False` | - |
| `bEnableDefenseOtherGuildPlayer` | `False` | ให้ฐาน/Pal ป้องกันพื้นที่จากผู้เล่นต่างกิลด์ | `True` / `False`<br>`True` ทำให้ระบบป้องกันตอบโต้คู่แข่งต่างกิลด์ | ใช้ `True` สำหรับ PvP/การบุกฐาน | พฤติกรรมขึ้นกับกติกา PvP อื่น |
| `BlockRespawnTime` | `5.000000` | Cooldown พื้นฐานก่อน Respawn หน่วยวินาที | ตัวเลขไม่ติดลบ<br>เพิ่ม = รอนานขึ้น; `0` = ไม่มีเวลาบล็อกพื้นฐาน | `5` Default, `30` รอครึ่งนาที | - |
| `RespawnPenaltyDurationThreshold` | `0.000000` | เกณฑ์เวลารอดชีวิตก่อนใช้ตัวคูณโทษ Respawn ในการตายครั้งถัดไป หน่วยวินาที | ตัวเลขไม่ติดลบ<br>`0` ทำให้เงื่อนไขพร้อมใช้ตลอด; เพิ่มเพื่อให้ใช้โทษเฉพาะรูปแบบการตายตามช่วงเวลา | `0` Default | ค่าขั้นสูงสำหรับ PvP/Hardcore |
| `RespawnPenaltyTimeScale` | `2.000000` | ตัวคูณเวลา Respawn penalty | ตัวเลข `0` ขึ้นไป<br>เพิ่ม = เวลารอนานขึ้น; ลด = สั้นลง; `0` อาจลบ penalty | `1` ไม่คูณเพิ่ม, `2` Default/สองเท่า | ทำงานร่วมกับ BlockRespawnTime และ Threshold |
| `bDisplayPvPItemNumOnWorldMap_BaseCamp` | `False` | แสดงจำนวนไอเทมเฉพาะ PvP ของฐานบนแผนที่ | `True` / `False`<br>`True` เปิดข้อมูลบนแผนที่ | เปิดเฉพาะเซิร์ฟ PvP ที่ใช้ระบบไอเทมดังกล่าว | - |
| `bDisplayPvPItemNumOnWorldMap_Player` | `False` | แสดงตำแหน่ง/จำนวนไอเทมเฉพาะ PvP ของผู้เล่นบนแผนที่ | `True` / `False`<br>`True` เปิดข้อมูลผู้เล่นบนแผนที่ | กระทบความลับตำแหน่งใน PvP | - |
| `AdditionalDropItemWhenPlayerKillingInPvPMode` | `"PlayerDropItem"` | Item ID ที่ดรอปเพิ่มเมื่อฆ่าผู้เล่น | ข้อความ/Item ID<br>เปลี่ยนชนิดรางวัล PvP | Default `"PlayerDropItem"` | มีผลเมื่อ bAdditionalDropItemWhenPlayerKillingInPvPMode=True; ต้องใช้ ID ที่เกมรองรับ |
| `AdditionalDropItemNumWhenPlayerKillingInPvPMode` | `1` | จำนวนไอเทมรางวัล PvP ที่ดรอป | จำนวนเต็มไม่ติดลบ<br>เพิ่ม = รางวัลมากขึ้น | `1` Default, `5` ดรอป 5 ชิ้น | มีผลเมื่อเปิดระบบดรอปเพิ่ม |
| `bAdditionalDropItemWhenPlayerKillingInPvPMode` | `False` | เปิดดรอปไอเทมพิเศษเมื่อฆ่าผู้เล่นใน PvP | `True` / `False`<br>`True` ใช้ Item ID และจำนวนจากสองค่าถัดไป | ปิดไว้หากไม่ใช้ระบบรางวัล PvP | - |

### 7. ฟีเจอร์โลก การเดินทาง UI และสิทธิ์ผู้เล่น

| Key | Default | ความหมาย | ค่าและทิศทาง | ตัวอย่างใช้งาน | หมายเหตุ |
|---|---:|---|---|---|---|
| `bEnableInvaderEnemy` | `True` | เปิด Raid/Invader ที่บุกฐาน | `True` / `False`<br>`True` มี Event บุกฐาน; `False` ปิด | เซิร์ฟสร้างบ้านสบายใช้ `False` | - |
| `bActiveUNKO` | `False` | เปิดระบบ UNKO/มูล Pal | `True` / `False`<br>`True` เปิดการสร้างไอเทมดังกล่าว; `False` ปิด | ปกติคง `False` | ค่าขั้นสูง/เชิงทดลองและอาจเปลี่ยนตามเวอร์ชัน |
| `bEnableAimAssistPad` | `True` | เปิด Aim Assist สำหรับ Controller | `True` / `False`<br>`True` ช่วยเล็งด้วยจอย | Default `True` | - |
| `bEnableAimAssistKeyboard` | `False` | เปิด Aim Assist สำหรับ Keyboard/Mouse | `True` / `False`<br>`True` ช่วยเล็งบนเมาส์/คีย์บอร์ด | Public/PvP มักใช้ `False` เพื่อความยุติธรรม | - |
| `bIsMultiplay` | `False` | Flag ภายในสำหรับ Multiplayer | `True` / `False`<br>Dedicated server จัดการโหมด Multiplayer เอง | คงค่า Default เว้นแต่มีเอกสารเฉพาะ | ค่า Reserved/ภายใน ไม่ใช่ ServerPlayerMaxNum |
| `bEnableNonLoginPenalty` | `True` | เปิดผลลงโทษเมื่อไม่ Login/ระบบ Offline penalty | `True` / `False`<br>`False` ปิดผลลงโทษที่เกี่ยวข้องกับการไม่เข้าเกม; `True` ใช้กติกาเกม | เซิร์ฟเพื่อนที่ไม่ได้เปิด 24/7 อาจใช้ `False` | รายละเอียดผลย่อยไม่ได้อธิบายครบในเอกสารทางการและอาจเปลี่ยนตามเวอร์ชัน |
| `bEnableFastTravel` | `True` | เปิด Fast Travel | `True` / `False`<br>`False` บังคับเดินทางด้วยตนเอง | Co-op ทั่วไปใช้ `True` | - |
| `bEnableFastTravelOnlyBaseCamp` | `False` | จำกัด Fast Travel ให้ใช้เฉพาะระหว่างฐาน | `True` / `False`<br>`True` จำกัดจุดเดินทาง; `False` ใช้จุด Fast Travel ตามปกติ | ต้องเปิด bEnableFastTravel ด้วย | - |
| `bIsStartLocationSelectByMap` | `False` | ให้ผู้เล่นเลือกจุดเกิดเริ่มต้นจากแผนที่ | `True` / `False`<br>`True` เลือกจุดเริ่มได้; `False` ใช้พฤติกรรมเริ่มต้นของเกม | ค่าเหมาะกับเซิร์ฟที่ต้องการกระจายผู้เล่น | - |
| `bExistPlayerAfterLogout` | `False` | คงร่างผู้เล่นไว้ในโลกหลัง Logout | `True` / `False`<br>`True` ตัวละครยังอยู่/อาจถูกโจมตี; `False` ร่างหายเมื่อออก | PvP survival อาจใช้ `True`; Co-op ใช้ `False` | - |
| `bInvisibleOtherGuildBaseCampAreaFX` | `False` | ซ่อนเอฟเฟกต์ขอบเขตฐานของกิลด์อื่น | `True` / `False`<br>ตามชื่อค่า: `True` ซ่อน; `False` แสดง | ใช้ `True` หากต้องการลดข้อมูลพื้นที่ของคู่แข่ง | ชื่อและพฤติกรรมอาจเปลี่ยนตามโหมด PvP |
| `bBuildAreaLimit` | `False` | เปิดข้อจำกัดการสร้างใกล้จุดสำคัญ เช่น Fast Travel | `True` / `False`<br>`True` ห้ามสร้างในพื้นที่สงวน; `False` ผ่อนคลายข้อจำกัด | Public server ควรใช้ `True` เพื่อลดการ Block จุดสำคัญ | - |
| `CoopPlayerMaxNum` | `4` | จำนวนผู้เล่นสูงสุดของ Co-op session | จำนวนเต็มบวก<br>เพิ่มเพดาน Co-op หากโหมดรองรับ | `4` Default | Dedicated Server ใช้ ServerPlayerMaxNum เป็นหลัก ค่านี้อาจไม่มีผล |
| `bShowPlayerList` | `False` | แสดงรายชื่อผู้เล่นออนไลน์ในเมนู ESC | `True` / `False`<br>`True` ผู้เล่นเห็นรายชื่อออนไลน์ | Public server อาจปิดเพื่อความเป็นส่วนตัว | - |
| `ChatPostLimitPerMinute` | `30` | จำนวนข้อความ Chat สูงสุดต่อนาทีต่อกลไกที่เกมกำหนด | จำนวนเต็มไม่ติดลบ<br>ลด = กัน Spam เข้ม; เพิ่ม = Chat ได้ถี่ | `10` เข้ม, `30` Default, `60` ผ่อนคลาย | ตั้งต่ำเกินไปอาจรบกวนการสนทนา |
| `bIsShowJoinLeftMessage` | `True` | แสดงข้อความเมื่อผู้เล่นเข้า/ออก | `True` / `False`<br>`True` ประกาศ Join/Leave ในเกม | เซิร์ฟใหญ่ปิดเพื่อลดข้อความรบกวน | - |
| `EnablePredatorBossPal` | `True` | เปิด Predator Boss Pal ในโลก | `True` / `False`<br>`True` ให้ Boss ประเภทนี้เกิด | ปิดหากไม่ต้องการ Event/ศัตรูชนิดนี้ | - |

### 5. ฐาน กิลด์ และประสิทธิภาพโลก

| Key | Default | ความหมาย | ค่าและทิศทาง | ตัวอย่างใช้งาน | หมายเหตุ |
|---|---:|---|---|---|---|
| `BaseCampMaxNum` | `128` | จำนวนฐานรวมสูงสุดทั้งเซิร์ฟเวอร์ | จำนวนเต็มบวก<br>เพิ่ม = รองรับฐานรวมมากขึ้นและเพิ่มโหลด | `64` ลดเพดาน, `128` Default | เป็นเพดานทั้งโลก |
| `BaseCampWorkerMaxNum` | `15` | จำนวน Pal ทำงานสูงสุดต่อฐาน | จำนวนเต็ม; สูงสุดตามเอกสาร `50`<br>เพิ่ม = ฐานผลิตได้มากขึ้นแต่ AI/CPU/RAM สูงขึ้น | `15` Default, `20` เหมาะกับเครื่องแรง, `50` เสี่ยงโหลดสูง | หนึ่งในค่าที่กระทบ Performance มากที่สุด |
| `bAutoResetGuildNoOnlinePlayers` | `False` | ลบ/รีเซ็ตกิลด์ที่ไม่มีสมาชิกออนไลน์ตามเวลาที่กำหนด | `True` / `False`<br>`True` เปิด Cleanup; `False` เก็บกิลด์ไว้ | Public server อาจใช้ `True`; เซิร์ฟเพื่อนควรใช้ `False` | ทำงานร่วมกับ AutoResetGuildTimeNoOnlinePlayers |
| `AutoResetGuildTimeNoOnlinePlayers` | `72.000000` | ระยะออฟไลน์ก่อน Auto Reset กิลด์ หน่วยชั่วโมง | ตัวเลข `0` ขึ้นไป<br>เพิ่ม = รอนานก่อนลบ; ลด = ลบเร็ว | `72` = 3 วัน, `168` = 7 วัน | ไม่มีผลเมื่อ bAutoResetGuildNoOnlinePlayers=False |
| `GuildPlayerMaxNum` | `20` | จำนวนสมาชิกสูงสุดต่อกิลด์ | จำนวนเต็มบวก<br>เพิ่ม = กิลด์ใหญ่ขึ้น; ลด = บังคับกิลด์เล็ก | `10` กลุ่มเล็ก, `20` Default, `32` กลุ่มใหญ่ | - |
| `BaseCampMaxNumInGuild` | `4` | จำนวนฐานสูงสุดต่อกิลด์ | จำนวนเต็ม; Default `4`, เอกสารระบุสูงสุด `10`<br>เพิ่ม = กิลด์สร้างฐานได้มากและโหลดเพิ่ม | `3` ประหยัดทรัพยากร, `4` Default, `10` สูงสุดที่ระบุ | - |
| `ServerReplicatePawnCullDistance` | `15000.000000` | ระยะ Sync Pal/ตัวละครจากผู้เล่น หน่วยเซนติเมตร | เอกสารระบุ `5000`–`15000`<br>เพิ่ม = เห็น/Sync ไกลขึ้นแต่ Network/CPU สูง; ลด = Sync ใกล้ลง | `5000` = 50 ม., `15000` = 150 ม. Default/ค่าสูงสุดที่ระบุ | ไม่ควรเกินช่วงทางการ |
| `ItemContainerForceMarkDirtyInterval` | `1.000000` | ช่วงบังคับ Sync Container ขณะเปิด UI หน่วยวินาที | ตัวเลขมากกว่า `0`<br>ลด = Sync ถี่ขึ้น/ทันใจแต่โหลด Network สูง; เพิ่ม = ลดโหลดแต่อาจเห็นของช้าลง | `0.5` ถี่, `1` Default, `2` เบาลง | ไม่แนะนำ `0` |
| `PlayerDataPalStorageUpdateCheckTickInterval` | `1.000000` | ช่วงตรวจอัปเดต Pal Storage ในข้อมูลผู้เล่น หน่วยวินาที | ตัวเลขมากกว่า `0`<br>ลด = ตรวจถี่ขึ้น/โหลดเพิ่ม; เพิ่ม = ตรวจช้าลง | `1` Default, `2` ลดความถี่ครึ่งหนึ่ง | ค่าขั้นสูง คง Default หากไม่จำเป็น |
| `GuildRejoinCooldownMinutes` | `0` | เวลารอก่อนเข้ากิลด์ใหม่/กลับเข้ากิลด์ หน่วยนาที | จำนวนเต็มไม่ติดลบ<br>`0` ไม่มี Cooldown; เพิ่มเพื่อกันสลับกิลด์เพื่อเลี่ยงกติกา | `60` = 1 ชั่วโมง, `1440` = 1 วัน | - |
| `AutoTransferMasterCheckIntervalSeconds` | `3600.000000` | ช่วงตรวจ Guild Master ที่ไม่ Active หน่วยวินาที | ตัวเลขบวก<br>ลด = ตรวจถี่/ใช้ CPU มากขึ้น; เพิ่ม = ตรวจช้าลง | `3600` ตรวจทุกชั่วโมง, `86400` วันละครั้ง | - |
| `AutoTransferMasterThresholdDays` | `14` | จำนวนวันที่ Guild Master ออฟไลน์ก่อนโอนตำแหน่ง | จำนวนเต็มไม่ติดลบ<br>ลด = โอนเร็ว; เพิ่ม = รอนาน | `7` หนึ่งสัปดาห์, `14` Default, `30` หนึ่งเดือน | - |
| `MaxGuildsPerFrame` | `10` | จำนวนกิลด์ที่ประมวลผลต่อ Server frame | จำนวนเต็มบวก<br>เพิ่ม = อัปเดตกิลด์เร็วขึ้นแต่ CPU spike สูงขึ้น; ลด = กระจายโหลดแต่สถานะอาจอัปเดตช้า | `5` ลดโหลดต่อเฟรม, `10` Default, `20` เร็วขึ้น | ค่าขั้นสูง ควรคง Default หากไม่มีปัญหา |
| `BuildingNameDisplayCacheTTLSeconds` | `60` | อายุ Cache ชื่อเจ้าของอาคาร หน่วยวินาที | จำนวนเต็มไม่ติดลบ<br>ลด = ชื่อสดขึ้นแต่ Query ถี่; เพิ่ม = ลดโหลดแต่ชื่ออาจค้าง | `0` ไม่ Cache/ตรวจถี่, `60` Default, `300` 5 นาที | ใช้ร่วมกับ bEnableBuildingPlayerUIdDisplay |

### 9. Server, Network, Password, RCON และ REST API

| Key | Default | ความหมาย | ค่าและทิศทาง | ตัวอย่างใช้งาน | หมายเหตุ |
|---|---:|---|---|---|---|
| `AutoSaveSpan` | `30.000000` | ช่วง Auto-save World หน่วยวินาที | ตัวเลขบวก; Default `30`<br>ลด = Save ถี่/เสียข้อมูลน้อยแต่ Disk I/O สูง; เพิ่ม = เบาลงแต่เสี่ยงสูญความคืบหน้ามากขึ้น | `10` ถี่, `30` Default, `300` ทุก 5 นาที | ไม่แนะนำ `0` |
| `ServerPlayerMaxNum` | `32` | จำนวนผู้เล่นพร้อมกันสูงสุดบน Dedicated Server | จำนวนเต็มบวก; Default `32`<br>เพิ่ม = รองรับคนมากขึ้นและใช้ทรัพยากรมากขึ้น | `8` กลุ่มเล็ก, `16` กลาง, `32` Default/เพดานทั่วไป | - |
| `ServerName` | `"Default Palworld Server"` | ชื่อเซิร์ฟเวอร์ที่แสดงให้ผู้เล่น | ข้อความใน `"..."`<br>เปลี่ยนชื่อที่แสดงใน Browser/ข้อมูลเซิร์ฟ | `ServerName="Palworld TH"` | หลีกเลี่ยง Quote ที่ไม่ได้ Escape |
| `ServerDescription` | `""` | คำอธิบายเซิร์ฟเวอร์ | ข้อความใน `"..."`<br>ใช้บอกกติกา/ช่องทางติดต่อสั้น ๆ | `ServerDescription="Co-op ไทย เล่นสบาย"` | - |
| `AdminPassword` | `""` | รหัสผู้ดูแลที่ใช้ Admin/RCON/REST | ข้อความรหัสผ่านที่คาดเดายาก<br>ว่าง = ไม่มีรหัส Admin ที่ใช้งานได้อย่างปลอดภัย | ใช้รหัสยาวอย่างน้อย 16 ตัวแบบสุ่ม | ในโปรเจกต์นี้ต้องตรงกับ `.env` หรือ `.env.host`; ห้ามเผยแพร่ |
| `ServerPassword` | `""` | รหัสผ่านสำหรับเข้าเล่น | ข้อความ; ว่าง = ไม่ต้องใช้รหัส<br>ตั้งค่าเพื่อจำกัดเฉพาะผู้ที่รู้รหัส | `ServerPassword="friends-only"` | ไม่ควรใช้รหัสเดียวกับ AdminPassword |
| `bAllowClientMod` | `True` | อนุญาต Client ที่เปิด Mod เชื่อมต่อ | `True` / `False`<br>`True` รองรับ Client mod; `False` เข้มงวดกว่า | Public server ที่เน้นความสะอาดใช้ `False` | ไม่ได้รับประกันว่า Mod ทุกตัวเข้ากันได้ |
| `PublicPort` | `8211` | Public port ที่ประกาศใน Community listing | จำนวน Port `1`–`65535`; Default `8211`<br>เปลี่ยนเฉพาะ Port ที่ประกาศ ไม่ได้เปลี่ยน Listening port ของเกม | `8211` Default | ต้องให้ตรงกับ NAT/Tunnel หากใช้ Community listing |
| `PublicIP` | `""` | Public IP ที่ประกาศสำหรับ Community listing | ข้อความ IP; ว่างให้ระบบตรวจเอง<br>ใส่เมื่อเกมตรวจ Public IP ผิดหรือมี NAT เฉพาะ | `PublicIP="203.0.113.10"` | เมื่อใช้ Playit/Radmin ไม่ควรเดาสุ่ม; ค่านี้ไม่ใช่ Local bind address |
| `RCONEnabled` | `False` | เปิด Remote Console | `True` / `False`<br>`True` ให้เครื่องมือ Admin เชื่อม RCON ได้ | โปรเจกต์ Dashboard อาจต้องใช้ตาม Workflow | อย่าเปิด Port RCON สู่ Internet โดยตรง |
| `RCONPort` | `25575` | Port ของ RCON | จำนวน Port; Default `25575`<br>เปลี่ยน Port ที่ RCON ฟัง | `25575` Default | ต้องตรงกับ Compose/Firewall/Host Agent |
| `Region` | `""` | Tag ภูมิภาคของเซิร์ฟเวอร์ | ข้อความ; ว่างได้<br>ใช้ช่วยจัดหมวด/ค้นหาเมื่อระบบรองรับ | `Region="Asia"` | ไม่ใช่ Time zone |
| `bUseAuth` | `True` | เปิดระบบ Authentication ของแพลตฟอร์ม | `True` / `False`<br>`True` ตรวจสิทธิ์ผู้เล่น; `False` ลดการตรวจสอบ | ควรคง `True` | ปิดอาจเพิ่มความเสี่ยงด้าน Identity/การปลอมผู้เล่น |
| `BanListURL` | `"https://b.palworldgame.com/api/banlist.txt"` | URL รายการ Ban ที่ Server โหลด | URL ใน `"..."`<br>เปลี่ยนแหล่ง Ban list | คง Default `https://b.palworldgame.com/api/banlist.txt` | อย่าใช้ URL ที่ไม่เชื่อถือ |
| `RESTAPIEnabled` | `False` | เปิด Palworld REST API | `True` / `False`<br>`True` ให้ Dashboard อ่านสถานะและสั่งงานได้ | โปรเจกต์นี้ต้องใช้ `True` | ห้ามเปิด REST API สู่ Internet โดยตรง |
| `RESTAPIPort` | `8212` | Port ของ REST API | จำนวน Port; Default `8212`<br>เปลี่ยน Port ที่ REST API ฟัง | `8212` Default | ต้องตรงกับ `.env`/`.env.host` และ Dashboard |
| `CrossplayPlatforms` | `(Steam,Xbox,PS5,Mac)` | แพลตฟอร์มที่อนุญาตให้เชื่อมต่อ | Array เช่น `(Steam,Xbox,PS5,Mac)`<br>ลบชื่อแพลตฟอร์มเพื่อไม่ให้แพลตฟอร์มนั้นเข้า | `(Steam)` เฉพาะ Steam; Default อนุญาตครบ | ต้องใช้ชื่อและตัวพิมพ์ตามที่เกมรองรับ |
| `bIsUseBackupSaveData` | `True` | เปิด Backup save ภายในเกม | `True` / `False`<br>`True` สร้างโฟลเดอร์ backup และหลายช่วงเวลา; เพิ่ม Disk I/O | ควรใช้ `True` ร่วมกับ Export ภายนอก | Backup ภายในไม่แทน Off-machine backup |
| `LogFormatType` | `Text` | รูปแบบ Log ของเกม | `Text` หรือ `Json`<br>`Json` เหมาะกับระบบเก็บ Log; `Text` อ่านง่าย | ใช้ `Text` ทั่วไป, `Json` สำหรับ Vector/ELK | ตรวจระบบ parser ก่อนเปลี่ยน |

### 8. Global Palbox และการเพิ่มค่าสถานะ

| Key | Default | ความหมาย | ค่าและทิศทาง | ตัวอย่างใช้งาน | หมายเหตุ |
|---|---:|---|---|---|---|
| `bAllowGlobalPalboxExport` | `True` | อนุญาตส่ง Pal ไป Global Palbox | `True` / `False`<br>`True` ส่ง Pal ออกจากโลกไป Global Palbox ได้ | Default `True`; ปิดเพื่อกันย้าย Pal ออกจากเซิร์ฟ | - |
| `bAllowGlobalPalboxImport` | `False` | อนุญาตนำ Pal จาก Global Palbox เข้าโลก | `True` / `False`<br>`True` นำ Pal จากโลกอื่นเข้ามาได้ | Public server ควรพิจารณาปิดเพื่อกันของนอกระบบ | Default `False` |
| `bAllowEnhanceStat_Health` | `True` | อนุญาตให้ผู้เล่นลงแต้มเพิ่มค่าสถานะ HP | `True` / `False`<br>`True` เพิ่ม HP ได้เมื่อ Level up; `False` ซ่อน/ปิดตัวเลือกนี้ | ปิดเป็น `False` หากต้องการล็อก Build ไม่ให้เพิ่ม HP | - |
| `bAllowEnhanceStat_Attack` | `True` | อนุญาตให้ผู้เล่นลงแต้มเพิ่มค่าสถานะ Attack | `True` / `False`<br>`True` เพิ่ม Attack ได้เมื่อ Level up; `False` ซ่อน/ปิดตัวเลือกนี้ | ปิดเป็น `False` หากต้องการล็อก Build ไม่ให้เพิ่ม Attack | - |
| `bAllowEnhanceStat_Stamina` | `True` | อนุญาตให้ผู้เล่นลงแต้มเพิ่มค่าสถานะ Stamina | `True` / `False`<br>`True` เพิ่ม Stamina ได้เมื่อ Level up; `False` ซ่อน/ปิดตัวเลือกนี้ | ปิดเป็น `False` หากต้องการล็อก Build ไม่ให้เพิ่ม Stamina | - |
| `bAllowEnhanceStat_Weight` | `True` | อนุญาตให้ผู้เล่นลงแต้มเพิ่มค่าสถานะ Carry Weight | `True` / `False`<br>`True` เพิ่ม Carry Weight ได้เมื่อ Level up; `False` ซ่อน/ปิดตัวเลือกนี้ | ปิดเป็น `False` หากต้องการล็อก Build ไม่ให้เพิ่ม Carry Weight | - |
| `bAllowEnhanceStat_WorkSpeed` | `True` | อนุญาตให้ผู้เล่นลงแต้มเพิ่มค่าสถานะ Work Speed | `True` / `False`<br>`True` เพิ่ม Work Speed ได้เมื่อ Level up; `False` ซ่อน/ปิดตัวเลือกนี้ | ปิดเป็น `False` หากต้องการล็อก Build ไม่ให้เพิ่ม Work Speed | - |

### 10. Voice Chat, UI Admin และค่าขั้นสูง

| Key | Default | ความหมาย | ค่าและทิศทาง | ตัวอย่างใช้งาน | หมายเหตุ |
|---|---:|---|---|---|---|
| `DenyTechnologyList` | `` | รายการ Technology ID ที่ห้ามปลด/ใช้ | Array ของข้อความ หรือว่าง<br>ใส่ ID เพื่อ Disable Technology เฉพาะรายการ | เช่น `DenyTechnologyList=("PALBOX","RepairBench")` | ต้องใช้ Technology ID ที่ถูกต้อง; พิมพ์ผิดอาจไม่เกิดผล |
| `bEnableVoiceChat` | `False` | เปิด Voice Chat ในเกม | `True` / `False`<br>`True` เปิดเสียงระยะใกล้ | ปิดหากใช้ Discord หรือไม่ต้องการเสียงในเกม | - |
| `VoiceChatMaxVolumeDistance` | `3000.000000` | ระยะที่เสียงยังดังเต็ม หน่วย Unreal (`100` หน่วย ≈ 1 เมตร) | ตัวเลขไม่ติดลบ<br>เพิ่ม = ได้ยินเต็มเสียงไกลขึ้น | `3000` ≈ 30 เมตร | ควรน้อยกว่า VoiceChatZeroVolumeDistance |
| `VoiceChatZeroVolumeDistance` | `15000.000000` | ระยะที่เสียงลดจนเป็นศูนย์ หน่วย Unreal | ตัวเลขไม่ติดลบ<br>เพิ่ม = ได้ยินไกลขึ้น | `15000` ≈ 150 เมตร | ควรมากกว่า MaxVolumeDistance |
| `bEnableBuildingPlayerUIdDisplay` | `False` | แสดง Player UID เจ้าของบนสิ่งปลูกสร้าง | `True` / `False`<br>`True` ช่วย Admin ตรวจเจ้าของ; `False` ซ่อน | Public server อาจเปิดสำหรับตรวจสอบ แต่มีผลด้าน Privacy | - |

---

## Preset ตัวอย่างที่นำไปใช้ได้ทันที

### เล่นกับเพื่อนแบบสบาย

```ini
ExpRate=2.000000
PalCaptureRate=1.500000
CollectionDropRate=2.000000
EnemyDropItemRate=1.500000
ItemWeightRate=0.500000
PalEggDefaultHatchingTime=0.500000
WorkSpeedRate=1.500000
DeathPenalty=Item
BuildObjectDeteriorationDamageRate=0.000000
```

### เล่นสบายมาก ไม่มีน้ำหนัก ของไม่เน่า ไข่ฟักทันที

```ini
ItemWeightRate=0.000000
ItemCorruptionMultiplier=0.000000
PalEggDefaultHatchingTime=0.000000
EquipmentDurabilityDamageRate=0.000000
PlayerStaminaDecreaceRate=0.500000
PalStomachDecreaceRate=0.500000
```

### Server เครื่องไม่แรง เน้นลดโหลด

```ini
PalSpawnNumRate=0.750000
BaseCampWorkerMaxNum=15
BaseCampMaxNumInGuild=3
DropItemMaxNum=1500
DropItemAliveMaxHours=0.500000
PhysicsActiveDropItemMaxNum=300
ServerReplicatePawnCullDistance=8000.000000
```

### PvP พื้นฐาน

```ini
bIsPvP=True
bEnablePlayerToPlayerDamage=True
bEnableFriendlyFire=False
bEnableDefenseOtherGuildPlayer=True
bCanPickupOtherGuildDeathPenaltyDrop=True
DeathPenalty=ItemAndEquipment
BlockRespawnTime=10.000000
```

---

## โครงสร้างไฟล์ที่ถูกต้อง

```ini
[/Script/Pal.PalGameWorldSettings]
OptionSettings=(Difficulty=None,ExpRate=2.000000,ItemWeightRate=0.500000,ServerName="Palworld TH",...)
```

- ทุก Key ต้องอยู่ภายในวงเล็บของ `OptionSettings=(...)`
- คั่นแต่ละค่าด้วย comma `,`
- ข้อความควรอยู่ใน double quote `"..."`
- ชื่อ Key ต้องตรงทุกตัว รวมตัวพิมพ์ใหญ่เล็กและคำสะกดเดิมของเกม
- อย่าแก้ `DefaultPalWorldSettings.ini` เพราะเกมไม่อ่านไฟล์นั้นเป็น Config ที่ใช้งานจริง

---

## เมื่อแก้ผ่าน Dashboard แล้วค่าไม่เปลี่ยน

ตรวจตามลำดับนี้:

1. กด **อัปเดตไฟล์** สำเร็จแล้วหรือยัง และกด **Restart Server** หลังจากนั้นแล้วหรือยัง
2. Dashboard เขียนไฟล์ของระบบถูกตำแหน่งหรือไม่ (`WindowsServer` หรือ `LinuxServer`)
3. Docker mode ตั้ง `PALWORLD_DISABLE_GENERATE_SETTINGS=true` แล้วหรือไม่ เพื่อกัน Environment เขียนทับ
4. `OptionSettings=(...)` มี comma, quote และวงเล็บครบหรือไม่
5. World มีไฟล์นี้หรือไม่:

```text
Pal/Saved/SaveGames/0/<WorldID>/WorldOption.sav
```

หากมี `WorldOption.sav` โดยเฉพาะ World ที่ย้ายจาก Single-player/Co-op เกมอาจอ่านค่า Gameplay จากไฟล์นี้แทน `PalWorldSettings.ini` ขณะที่ค่า Server/Network บางส่วนยังอ่านจาก `.ini` อยู่ อย่าลบไฟล์นี้ทันทีบน World จริง ให้ Export backup ก่อน แล้วทดสอบบนสำเนา World หรือใช้เครื่องมือที่รองรับการสร้าง/แก้ `WorldOption.sav` โดยเฉพาะ

---

## ค่าที่กระทบ Performance มากที่สุด

| ค่า | เหตุผล | แนวทาง |
|---|---|---|
| `PalSpawnNumRate` | เพิ่มจำนวน AI ในโลก | เพิ่มทีละ `0.25` และดู CPU/FPS |
| `BaseCampWorkerMaxNum` | เพิ่ม Pal AI ทุกฐาน | เริ่ม 15–20 ก่อน |
| `BaseCampMaxNumInGuild` / `BaseCampMaxNum` | เพิ่มจำนวนฐานและอาคาร | จำกัดตามจำนวนผู้เล่นจริง |
| `DropItemMaxNum` / `DropItemAliveMaxHours` | เพิ่มวัตถุตกพื้นสะสม | ลดจำนวนและเวลาคงอยู่ |
| `PhysicsActiveDropItemMaxNum` | Physics ของไอเทมใช้ CPU | ตั้ง Limit แทน `-1` หากของตกเยอะ |
| `ServerReplicatePawnCullDistance` | Sync Actor ไกลขึ้น | ใช้ 8,000–15,000 ตาม Network |
| `AutoSaveSpan` | Save ถี่เพิ่ม Disk I/O | 30 วินาทีเป็นจุดเริ่มที่สมดุล |

---

## DefaultPalWorldSettings.ini ฉบับอ้างอิง

> ใช้สำหรับเปรียบเทียบเท่านั้น การแก้ไฟล์ Default ไม่ทำให้ Server เปลี่ยนค่า

```ini
[/Script/Pal.PalGameWorldSettings]
OptionSettings=(Difficulty=None,RandomizerType=None,RandomizerSeed="",bIsRandomizerPalLevelRandom=False,DayTimeSpeedRate=1.000000,NightTimeSpeedRate=1.000000,ExpRate=1.000000,PalCaptureRate=1.000000,PalSpawnNumRate=1.000000,PalDamageRateAttack=1.000000,PalDamageRateDefense=1.000000,PlayerDamageRateAttack=1.000000,PlayerDamageRateDefense=1.000000,PlayerStomachDecreaceRate=1.000000,PlayerStaminaDecreaceRate=1.000000,PlayerAutoHPRegeneRate=1.000000,PlayerAutoHpRegeneRateInSleep=1.000000,PalStomachDecreaceRate=1.000000,PalStaminaDecreaceRate=1.000000,PalAutoHPRegeneRate=1.000000,PalAutoHpRegeneRateInSleep=1.000000,BuildObjectHpRate=1.000000,BuildObjectDamageRate=1.000000,BuildObjectDeteriorationDamageRate=1.000000,CollectionDropRate=1.000000,CollectionObjectHpRate=1.000000,CollectionObjectRespawnSpeedRate=1.000000,EnemyDropItemRate=1.000000,DeathPenalty=Item,bEnablePlayerToPlayerDamage=False,bEnableFriendlyFire=False,bEnableInvaderEnemy=True,bActiveUNKO=False,bEnableAimAssistPad=True,bEnableAimAssistKeyboard=False,DropItemMaxNum=3000,PhysicsActiveDropItemMaxNum=-1,DropItemMaxNum_UNKO=100,BaseCampMaxNum=128,BaseCampWorkerMaxNum=15,DropItemAliveMaxHours=1.000000,bAutoResetGuildNoOnlinePlayers=False,AutoResetGuildTimeNoOnlinePlayers=72.000000,GuildPlayerMaxNum=20,BaseCampMaxNumInGuild=4,PalEggDefaultHatchingTime=1.000000,WorkSpeedRate=1.000000,AutoSaveSpan=30.000000,bIsMultiplay=False,bIsPvP=False,bHardcore=False,bPalLost=False,bCharacterRecreateInHardcore=False,bCanPickupOtherGuildDeathPenaltyDrop=False,bEnableNonLoginPenalty=True,bEnableFastTravel=True,bEnableFastTravelOnlyBaseCamp=False,bIsStartLocationSelectByMap=False,bExistPlayerAfterLogout=False,bEnableDefenseOtherGuildPlayer=False,bInvisibleOtherGuildBaseCampAreaFX=False,bBuildAreaLimit=False,ItemWeightRate=1.000000,CoopPlayerMaxNum=4,ServerPlayerMaxNum=32,ServerName="Default Palworld Server",ServerDescription="",AdminPassword="",ServerPassword="",bAllowClientMod=True,PublicPort=8211,PublicIP="",RCONEnabled=False,RCONPort=25575,Region="",bUseAuth=True,BanListURL="https://b.palworldgame.com/api/banlist.txt",RESTAPIEnabled=False,RESTAPIPort=8212,bShowPlayerList=False,ChatPostLimitPerMinute=30,CrossplayPlatforms=(Steam,Xbox,PS5,Mac),bIsUseBackupSaveData=True,LogFormatType=Text,bIsShowJoinLeftMessage=True,SupplyDropSpan=180,EnablePredatorBossPal=True,MaxBuildingLimitNum=0,ServerReplicatePawnCullDistance=15000.000000,bAllowGlobalPalboxExport=True,bAllowGlobalPalboxImport=False,EquipmentDurabilityDamageRate=1.000000,ItemContainerForceMarkDirtyInterval=1.000000,PlayerDataPalStorageUpdateCheckTickInterval=1.000000,ItemCorruptionMultiplier=1.000000,MonsterFarmActionSpeedRate=1.000000,DenyTechnologyList=,GuildRejoinCooldownMinutes=0,AutoTransferMasterCheckIntervalSeconds=3600.000000,AutoTransferMasterThresholdDays=14,MaxGuildsPerFrame=10,BlockRespawnTime=5.000000,RespawnPenaltyDurationThreshold=0.000000,RespawnPenaltyTimeScale=2.000000,bDisplayPvPItemNumOnWorldMap_BaseCamp=False,bDisplayPvPItemNumOnWorldMap_Player=False,AdditionalDropItemWhenPlayerKillingInPvPMode="PlayerDropItem",AdditionalDropItemNumWhenPlayerKillingInPvPMode=1,bAdditionalDropItemWhenPlayerKillingInPvPMode=False,bEnableVoiceChat=False,VoiceChatMaxVolumeDistance=3000.000000,VoiceChatZeroVolumeDistance=15000.000000,bAllowEnhanceStat_Health=True,bAllowEnhanceStat_Attack=True,bAllowEnhanceStat_Stamina=True,bAllowEnhanceStat_Weight=True,bAllowEnhanceStat_WorkSpeed=True,bEnableBuildingPlayerUIdDisplay=False,BuildingNameDisplayCacheTTLSeconds=60)
```

---

## แหล่งอ้างอิง

- [Pocketpair — Palworld Server Guide: Configuration parameters](https://docs.palworldgame.com/settings-and-operation/configuration/)
- [Palworld 1.0 DefaultPalWorldSettings.ini snapshot](https://raw.githubusercontent.com/KJAyano/Palworld-Config-Parser-Tool/main/DefaultPalWorldSettings.ini)
- [Host Havoc — Palworld 1.0 settings generator/reference](https://hosthavoc.com/tools/palworld/server-settings-generator)
- [Official Pocketpair dedicated-server Docker repository](https://github.com/pocketpairjp/palworld-dedicated-server-docker)

> ค่า Default และชื่อ Key ควรตรวจเทียบกับ `DefaultPalWorldSettings.ini` ที่มากับ Dedicated Server เวอร์ชันที่ติดตั้งจริงทุกครั้งหลังเกมอัปเดต เพราะ Pocketpair อาจเพิ่ม ลบ หรือเปลี่ยนพฤติกรรมของค่าในอนาคต


### สถานะค่าร่าง ค่าในไฟล์ และค่าที่ Server ใช้อยู่

หน้า Config แยกสถานะเป็น 3 ชั้นเพื่อป้องกันความสับสน:

- **Server ใช้อยู่**: ค่าจาก REST `GET /settings` ของ Process ที่กำลังรัน
- **ในไฟล์**: ค่าที่อ่านจาก `PalWorldSettings.ini` และจะถูกโหลดเมื่อ Restart
- **ค่าร่าง**: ค่าที่แก้ในหน้าเว็บแต่ยังไม่ได้กด **อัปเดตไฟล์**

หลังอัปเดตไฟล์สำเร็จ ค่าจะถูกย้ายออกจากรายการร่างและแสดงในคอลัมน์ **ในไฟล์ — รอ Restart** ปุ่ม Restart จะเตือนเฉพาะค่าร่างที่ยังไม่ได้เขียน ไม่เตือนค่าที่บันทึกลงไฟล์แล้ว

เมื่อเริ่ม Restart ระบบจะล็อกสำเนา `PalWorldSettings.ini` ล่าสุดไว้ก่อน จากนั้นแจ้งผู้เล่นและหยุด Server ให้สนิท แล้วเขียนสำเนาที่ล็อกไว้กลับลงไฟล์อีกครั้งก่อนเปิด Server วิธีนี้ป้องกันกรณี Process เดิมเขียนค่า Runtime เก่าทับไฟล์ระหว่าง Shutdown หลัง REST API พร้อม ระบบจะอ่าน `GET /settings` และตรวจเฉพาะค่าที่รอ Restart หากค่าไม่ตรง Job จะเป็น `failed` พร้อมระบุค่าที่ไม่ตรง แทนการขึ้น `completed` ผิด ๆ

เมื่อการตรวจผ่าน หน้า Config จะโหลดทั้ง `GET /settings` และไฟล์ใหม่อัตโนมัติ สถานะ **อัปเดตไฟล์แล้ว — รอ Restart** และตารางค่าที่รอใช้จะหายทันทีโดยไม่ต้อง Refresh หน้า นอกจากนี้ `DenyTechnologyList=` และ `DenyTechnologyList=()` จะถูกตีความเป็นรายการว่าง `[]` เหมือนกับ REST API จึงไม่แสดงเป็นความต่างปลอม
